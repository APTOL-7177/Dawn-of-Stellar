"""
호감도 확인 UI

파티원 간 호감도 레벨, 포인트, 해금된 연계스킬/체인어빌리티를 표시합니다.
게임 메뉴에서 접근 가능합니다.
"""

from typing import List, Any, Optional, Tuple
from src.core.logger import get_logger
from src.character.affinity import AffinityManager, AffinityLevel
from src.ui.input_handler import GameAction, iter_game_input, unified_input_handler
from src.ui.pointer import PointerButton, PointerDispatchResult, PointerDispatcher, PointerEvent, PointerEventKind, PointerRegion

logger = get_logger("affinity_ui")


class AffinityUI:
    """호감도 확인 UI"""

    # 호감도 레벨별 색상
    LEVEL_COLORS = {
        0: (120, 120, 120),   # 회색 - 모르는 사이
        1: (200, 200, 200),   # 연회색 - 동료
        2: (100, 200, 255),   # 하늘색 - 신뢰
        3: (100, 255, 150),   # 연두색 - 친밀
        4: (255, 180, 100),   # 주황색 - 깊은 유대
        5: (255, 215, 0),     # 금색 - 영혼의 동반자
    }

    def __init__(self, console: Any, context: Any):
        self.console = console
        self.context = context
        self.selected_pair_index = 0
        self.scroll_offset = 0
        self.detail_mode = False  # True면 상세 보기
        self._pending_gauges = []  # pixel overlay 게이지 큐

    def show(self, affinity_manager: AffinityManager, party_jobs: List[str], party_names: dict):
        """
        호감도 UI 표시

        Args:
            affinity_manager: AffinityManager 인스턴스
            party_jobs: 파티 직업 ID 리스트
            party_names: {job_id: display_name} 매핑
        """
        # 파티 내 모든 쌍 수집
        pairs = []
        for i in range(len(party_jobs)):
            for j in range(i + 1, len(party_jobs)):
                job_a, job_b = sorted([party_jobs[i], party_jobs[j]])
                level = affinity_manager.get_level(job_a, job_b)
                points = affinity_manager.get_points(job_a, job_b)
                pairs.append({
                    "job_a": job_a, "job_b": job_b,
                    "name_a": party_names.get(job_a, job_a),
                    "name_b": party_names.get(job_b, job_b),
                    "level": level, "points": points
                })

        # 포인트 내림차순 정렬
        pairs.sort(key=lambda p: p["points"], reverse=True)

        if not pairs:
            return

        self.selected_pair_index = 0
        self.scroll_offset = 0
        running = True

        while running:
            self._render(pairs, affinity_manager, party_jobs)
            # pixel overlay 스무스 게이지 등록
            if hasattr(self.context, 'add_pixel_overlay') and self._pending_gauges:
                gauges = list(self._pending_gauges)
                self._pending_gauges.clear()
                tw = getattr(self.context, 'tile_width', 10)
                th = getattr(self.context, 'tile_height', 13)
                def _gauge_overlay(dt, _g=gauges, _tw=tw, _th=th):
                    from src.ui.raylib_backend.smooth_gauge import draw_smooth_gauge
                    for gx, gy, gw, ratio, ci, wound in _g:
                        if isinstance(ci, str):
                            draw_smooth_gauge(gx * _tw, gy * _th, gw * _tw, _th, ratio, kind=ci, wound_ratio=wound)
                        else:
                            draw_smooth_gauge(gx * _tw, gy * _th, gw * _tw, _th, ratio, custom_color=ci, wound_ratio=wound)
                self.context.add_pixel_overlay(_gauge_overlay)
            self.context.present(self.console)

            for action, event in iter_game_input():
                pointer_event = unified_input_handler.process_pointer_event(event) if event is not None else None
                if pointer_event is not None:
                    self.handle_pointer_event(pointer_event, pairs)
                    continue
                if action == GameAction.QUIT:
                    running = False
                    break
                result = self._handle_action(action, pairs, affinity_manager, party_jobs)
                if result == "close":
                    running = False
                    break

    def _render(self, pairs: list, affinity_manager: AffinityManager, party_jobs: List[str]):
        """메인 화면 렌더링"""
        width = self.console.width
        height = self.console.height

        # 전체 화면 클리어
        self.console.clear()

        # 타이틀
        title = "[ 호감도 ]"
        self.console.print(width // 2 - len(title) // 2, 1, title, fg=(255, 220, 100))

        if self.detail_mode:
            self._render_detail(pairs, affinity_manager, party_jobs)
        else:
            self._render_list(pairs)

        # 하단 안내
        if self.detail_mode:
            help_text = "[ESC/B] 목록으로  [↑↓] 스크롤"
        else:
            help_text = "[↑↓] 선택  [Enter/A] 상세  [ESC/B] 닫기"
        self.console.print(2, height - 2, help_text, fg=(150, 150, 150))

    def _render_list(self, pairs: list):
        """쌍 목록 렌더링"""
        width = self.console.width
        max_visible = min(len(pairs), self.console.height - 6)

        for i in range(max_visible):
            idx = i + self.scroll_offset
            if idx >= len(pairs):
                break

            pair = pairs[idx]
            y = 3 + i * 2
            is_selected = (idx == self.selected_pair_index)
            level: AffinityLevel = pair["level"]
            color = self.LEVEL_COLORS.get(level.value, (200, 200, 200))

            cursor = ">" if is_selected else " "
            bg = (30, 30, 50) if is_selected else (0, 0, 0)

            # 이름과 레벨
            name_text = f"{cursor} {pair['name_a']} ↔ {pair['name_b']}"
            self.console.print(2, y, name_text, fg=color, bg=bg)

            # 레벨 및 포인트
            level_text = f"Lv{level.value} {level.display_name} [{pair['points']}pt]"
            self.console.print(width - len(level_text) - 2, y, level_text, fg=color, bg=bg)

            # 게이지 바
            if level.next_level_points:
                # 현재 레벨 시작 포인트
                current_threshold = {0: 0, 1: 50, 2: 150, 3: 300, 4: 500}.get(level.value, 0)
                next_threshold = level.next_level_points
                progress = (pair["points"] - current_threshold) / (next_threshold - current_threshold)
                progress = min(1.0, max(0.0, progress))
                bar_width = 20
                _bg = tuple(max(0, c // 4) for c in color)
                self.console.draw_rect(4, y + 1, bar_width, 1, ord(" "), bg=_bg)
                _filled = max(0, int(bar_width * progress))
                if _filled > 0:
                    self.console.draw_rect(4, y + 1, _filled, 1, ord(" "), bg=color)
                self._pending_gauges.append((4, y + 1, bar_width, progress, color, 0.0))  # custom_color tuple
            else:
                self.console.print(4, y + 1, "████████████████████ MAX", fg=(255, 215, 0), bg=bg)

    def pointer_regions(self, pairs: list | None = None) -> tuple[PointerRegion, ...]:
        if pairs is None:
            pairs = getattr(self, "_pointer_pairs", [])
        if self.detail_mode:
            return (PointerRegion("detail", 0, 3, self.console.width, self.console.height - 6, GameAction.CANCEL, "상세 보기 | 우클릭으로 목록"),)
        max_visible = min(len(pairs), self.console.height - 6)
        regions: list[PointerRegion] = []
        for index in range(max_visible):
            actual_index = self.scroll_offset + index
            if actual_index >= len(pairs):
                break
            pair = pairs[actual_index]
            regions.append(PointerRegion(f"pair:{actual_index}", 2, 3 + index * 2, self.console.width - 4, 2, GameAction.CONFIRM, self._pair_tooltip(pair)))
        return tuple(regions)

    def handle_pointer_event(self, event: PointerEvent, pairs: list | None = None) -> PointerDispatchResult:
        if pairs is not None:
            self._pointer_pairs = pairs
        active_pairs = pairs if pairs is not None else getattr(self, "_pointer_pairs", [])
        if event.kind is PointerEventKind.WHEEL:
            action = GameAction.MOVE_UP if event.wheel_delta > 0 else GameAction.MOVE_DOWN if event.wheel_delta < 0 else None
            if action is not None and active_pairs:
                self._handle_action(action, active_pairs, None, [])
            return PointerDispatchResult(event=event, action=action)
        if event.kind is PointerEventKind.CLICK and event.button is PointerButton.RIGHT:
            action = GameAction.CANCEL
            result = self._handle_action(action, active_pairs, None, []) if active_pairs else None
            return PointerDispatchResult(event=event, action=action, value=result)
        result = PointerDispatcher(self.pointer_regions(active_pairs)).dispatch(event)
        if result.hovered_region_id and result.hovered_region_id.startswith("pair:"):
            self.selected_pair_index = int(result.hovered_region_id.split(":", 1)[1])
        if event.kind is PointerEventKind.CLICK and event.button is PointerButton.LEFT and active_pairs:
            value = self._handle_action(GameAction.CONFIRM, active_pairs, None, [])
            return result.with_value(value)
        return result

    def _pair_tooltip(self, pair: Any) -> str:
        level = pair["level"]
        return f"{pair['name_a']} ↔ {pair['name_b']} | Lv{level.value} {level.display_name} | {pair['points']}pt"

    def _render_detail(self, pairs: list, affinity_manager: AffinityManager, party_jobs: List[str]):
        """상세 보기 렌더링"""
        if self.selected_pair_index >= len(pairs):
            return

        pair = pairs[self.selected_pair_index]
        level: AffinityLevel = pair["level"]
        color = self.LEVEL_COLORS.get(level.value, (200, 200, 200))

        y = 3

        # 캐릭터 이름
        header = f"{pair['name_a']} ↔ {pair['name_b']}"
        self.console.print(4, y, header, fg=color)
        y += 1

        # 레벨 및 포인트
        self.console.print(4, y, f"관계: Lv{level.value} {level.display_name}", fg=color)
        y += 1
        self.console.print(4, y, f"포인트: {pair['points']}", fg=(200, 200, 200))
        y += 1

        # 보너스
        bonus = level.gauge_charge_bonus
        if bonus > 0:
            self.console.print(4, y, f"게이지 충전 보너스: +{bonus:.0%}", fg=(100, 255, 100))
            y += 1

        y += 1

        # 해금된 연계스킬
        self.console.print(4, y, "[ 연계스킬 ]", fg=(100, 200, 255))
        y += 1

        bond_skills = affinity_manager.get_unlocked_bond_skills(pair["job_a"], [pair["job_b"]])
        bond_skills += affinity_manager.get_unlocked_bond_skills(pair["job_b"], [pair["job_a"]])
        if bond_skills:
            for skill, ally, lvl in bond_skills:
                chance = skill.get_trigger_chance(level.value)
                self.console.print(6, y, f"- {skill.name} (발동 {chance:.0%})", fg=(180, 220, 255))
                y += 1
                if skill.description:
                    desc = skill.description[:self.console.width - 10]
                    self.console.print(8, y, desc, fg=(150, 150, 150))
                    y += 1
        else:
            self.console.print(6, y, "(해금된 연계스킬 없음)", fg=(120, 120, 120))
            y += 1

        y += 1

        # 해금된 체인어빌리티
        self.console.print(4, y, "[ 체인어빌리티 ]", fg=(255, 180, 100))
        y += 1

        chain_abs = affinity_manager.get_unlocked_chain_abilities(pair["job_a"], [pair["job_b"]])
        chain_abs += affinity_manager.get_unlocked_chain_abilities(pair["job_b"], [pair["job_a"]])
        if chain_abs:
            for ability, ally, lvl in chain_abs:
                chance = ability.get_trigger_chance(level.value)
                self.console.print(
                    6, y,
                    f"- {ability.name} (발동 {chance:.0%}, 비용 {ability.gauge_cost})",
                    fg=(255, 200, 130)
                )
                y += 1
                if ability.description:
                    desc = ability.description[:self.console.width - 10]
                    self.console.print(8, y, desc, fg=(150, 150, 150))
                    y += 1
        else:
            self.console.print(6, y, "(해금된 체인어빌리티 없음)", fg=(120, 120, 120))
            y += 1

    def _handle_action(self, action: GameAction, pairs: list, affinity_manager, party_jobs) -> Optional[str]:
        """GameAction 입력 처리"""
        if self.detail_mode:
            if action in (GameAction.CANCEL, GameAction.ESCAPE):
                self.detail_mode = False
            return None

        if action == GameAction.MOVE_UP:
            self.selected_pair_index = max(0, self.selected_pair_index - 1)
            # 스크롤 조정
            if self.selected_pair_index < self.scroll_offset:
                self.scroll_offset = self.selected_pair_index
        elif action == GameAction.MOVE_DOWN:
            self.selected_pair_index = min(len(pairs) - 1, self.selected_pair_index + 1)
            max_visible = self.console.height - 6
            if self.selected_pair_index >= self.scroll_offset + max_visible // 2:
                self.scroll_offset = min(
                    len(pairs) - max_visible // 2,
                    self.selected_pair_index - max_visible // 2 + 1
                )
        elif action == GameAction.CONFIRM:
            self.detail_mode = True
        elif action in (GameAction.CANCEL, GameAction.ESCAPE):
            return "close"

        return None
