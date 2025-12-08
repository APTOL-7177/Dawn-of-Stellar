"""
Credits UI - 크레딧 화면

페이드인/페이드아웃 방식의 영화 스타일 크레딧 화면
"""

import tcod.console
import tcod.event
import math
import time
from typing import List, Tuple

from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, unified_input_handler
from src.core.logger import get_logger


class CreditsUI:
    """
    영화 스타일 크레딧 화면 (페이드인/페이드아웃)
    
    각 섹션이 순차적으로 나타났다 사라지는 방식
    """

    def __init__(self, screen_width: int = 80, screen_height: int = 50):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.logger = get_logger("credits_ui")
        
        # 타이밍 관련
        self.start_time = time.time()
        self.current_section = 0
        
        # 닫기 플래그
        self.should_close = False
        
        # 애니메이션 프레임
        self.animation_frame = 0
        
        # 배경 별 위치
        self.star_positions = []
        self._generate_stars()
        
        # 크레딧 섹션 정의 (각 섹션별 표시 시간)
        self.credits_sections = self._build_sections()
        
        # 전체 재생 시간 계산
        self.total_duration = sum(s["duration"] for s in self.credits_sections)
    
    def _generate_stars(self):
        """배경 별 생성"""
        import random
        self.star_positions = []
        for _ in range(25):
            x = random.randint(0, self.screen_width - 1)
            y = random.randint(0, self.screen_height - 1)
            brightness = random.randint(0, 10)
            speed = random.uniform(0.5, 2.0)
            self.star_positions.append([x, y, brightness, speed])
    
    def _build_sections(self) -> List[dict]:
        """
        크레딧 섹션 구성
        각 섹션은 lines(표시할 줄들), duration(표시 시간), fade_time(페이드 시간)
        """
        # 색상 정의
        gold = (255, 215, 100)
        bright_gold = (255, 235, 150)
        silver = (200, 200, 220)
        white = (255, 255, 255)
        light_blue = (150, 200, 255)
        dim = (120, 120, 140)
        
        sections = [
            # 타이틀
            {
                "lines": [
                    ("DAWN OF STELLAR", bright_gold),
                    ("별빛의 여명", gold),
                ],
                "duration": 18.0,
                "fade_time": 3.0
            },
            # 제작자
            {
                "lines": [
                    ("CREATED BY", silver),
                    ("", white),
                    ("앱톨", bright_gold),
                    ("APTOL", gold),
                ],
                "duration": 20.0,
                "fade_time": 3.0
            },
            # 게임 기획
            {
                "lines": [
                    ("GAME DESIGN", silver),
                    ("게임 기획", dim),
                    ("", white),
                    ("앱톨", white),
                ],
                "duration": 16.0,
                "fade_time": 2.5
            },
            # 시스템 설계
            {
                "lines": [
                    ("SYSTEM DESIGN", silver),
                    ("시스템 설계", dim),
                    ("", white),
                    ("ATB + BRV 전투 시스템", light_blue),
                    ("35종 직업 시스템", light_blue),
                    ("로그라이크 던전 생성", light_blue),
                ],
                "duration": 18.0,
                "fade_time": 2.5
            },
            # 프로그래밍
            {
                "lines": [
                    ("PROGRAMMING", silver),
                    ("프로그래밍", dim),
                    ("", white),
                    ("앱톨", white),
                ],
                "duration": 16.0,
                "fade_time": 2.5
            },
            # 엔진 & 프레임워크
            {
                "lines": [
                    ("ENGINE & FRAMEWORK", silver),
                    ("엔진 & 프레임워크", dim),
                    ("", white),
                    ("Python 3.10+", light_blue),
                    ("Pygame", light_blue),
                    ("TCOD", light_blue),
                ],
                "duration": 16.0,
                "fade_time": 2.5
            },
            # 아트
            {
                "lines": [
                    ("ART DIRECTION", silver),
                    ("아트 디렉션", dim),
                    ("", white),
                    ("앱톨", white),
                ],
                "duration": 14.0,
                "fade_time": 2.0
            },
            # 사운드
            {
                "lines": [
                    ("SOUND & MUSIC", silver),
                    ("사운드 & 음악", dim),
                    ("", white),
                    ("앱톨", white),
                ],
                "duration": 14.0,
                "fade_time": 2.0
            },
            # 게임 특징
            {
                "lines": [
                    ("GAME FEATURES", silver),
                    ("게임 특징", dim),
                    ("", white),
                    ("★ Final Fantasy 스타일 ATB 전투", light_blue),
                    ("★ BRV/HP 공격 전략 시스템", light_blue),
                    ("★ 35종의 고유한 직업", light_blue),
                    ("★ 52종의 요리 레시피", light_blue),
                ],
                "duration": 20.0,
                "fade_time": 2.5
            },
            # 게임 특징 2
            {
                "lines": [
                    ("GAME FEATURES", silver),
                    ("게임 특징", dim),
                    ("", white),
                    ("★ 연금술 시스템", light_blue),
                    ("★ 팀워크 스킬", light_blue),
                    ("★ 멀티플레이어 지원", light_blue),
                    ("★ 메타 진행 시스템", light_blue),
                ],
                "duration": 20.0,
                "fade_time": 2.5
            },
            # 스페셜 땡스
            {
                "lines": [
                    ("SPECIAL THANKS", silver),
                    ("특별한 감사", dim),
                    ("", white),
                    ("플레이해 주신 모든 분들께", white),
                    ("감사드립니다", white),
                    ("", white),
                    ("Thank you for playing!", gold),
                ],
                "duration": 22.0,
                "fade_time": 3.0
            },
            # 저작권
            {
                "lines": [
                    ("© 2024-2025 APTOL", dim),
                    ("All Rights Reserved", dim),
                    ("", white),
                    ("VERSION 6.1.0", gold),
                ],
                "duration": 18.0,
                "fade_time": 3.0
            },
            # 마무리
            {
                "lines": [
                    ("Dawn of Stellar", bright_gold),
                    ("별빛의 여명", gold),
                    ("", white),
                    ("별빛이 당신의 여정을 비추길...", light_blue),
                    ("May the starlight guide your journey...", silver),
                ],
                "duration": 28.0,
                "fade_time": 4.0
            },
        ]
        
        return sections
    
    def handle_input(self, action: GameAction) -> bool:
        """입력 처리"""
        if action in (GameAction.CONFIRM, GameAction.CANCEL, GameAction.ESCAPE):
            self.should_close = True
            return True
        
        # 다음 섹션으로 스킵
        if action == GameAction.MOVE_DOWN or action == GameAction.MOVE_RIGHT:
            self._skip_to_next_section()
        
        return False
    
    def _skip_to_next_section(self):
        """다음 섹션으로 스킵"""
        elapsed = time.time() - self.start_time
        accumulated = 0.0
        
        for i, section in enumerate(self.credits_sections):
            accumulated += section["duration"]
            if elapsed < accumulated:
                # 현재 섹션의 끝으로 이동
                self.start_time = time.time() - accumulated
                break
    
    def _get_current_section_and_alpha(self) -> Tuple[int, float]:
        """현재 섹션 인덱스와 알파값 계산"""
        elapsed = time.time() - self.start_time
        accumulated = 0.0
        
        for i, section in enumerate(self.credits_sections):
            section_start = accumulated
            section_end = accumulated + section["duration"]
            fade_time = section["fade_time"]
            
            if elapsed < section_end:
                # 현재 이 섹션 표시 중
                time_in_section = elapsed - section_start
                
                # 페이드인
                if time_in_section < fade_time:
                    alpha = time_in_section / fade_time
                # 페이드아웃
                elif time_in_section > section["duration"] - fade_time:
                    remaining = section["duration"] - time_in_section
                    alpha = remaining / fade_time
                # 완전히 보이는 상태
                else:
                    alpha = 1.0
                
                return i, max(0.0, min(1.0, alpha))
            
            accumulated = section_end
        
        # 모든 섹션 종료
        return len(self.credits_sections), 0.0
    
    def render(self, console: tcod.console.Console) -> None:
        """크레딧 렌더링"""
        self.animation_frame += 1
        
        # 배경 클리어 (어두운 우주 배경)
        console.clear()
        
        # 어두운 그라데이션 배경
        for y in range(self.screen_height):
            gradient_intensity = max(0, int(5 + (y / self.screen_height) * 15))
            r = max(0, gradient_intensity // 3)
            g = max(0, gradient_intensity // 4)
            b = max(0, gradient_intensity)
            for x in range(self.screen_width):
                console.rgb[y, x] = (ord(' '), (r, g, b), (r, g, b))
        
        # 배경 별 렌더링
        for star in self.star_positions:
            x, y, brightness, speed = star
            phase = (self.animation_frame + brightness * 10) / (20.0 / speed)
            current_brightness = max(0, min(255, int(80 + 100 * math.sin(phase))))
            star_color = (current_brightness, current_brightness, 200)
            
            if 0 <= x < self.screen_width and 0 <= y < self.screen_height:
                console.print(x, y, "·", fg=star_color)
        
        # 현재 섹션 및 알파값 가져오기
        section_idx, alpha = self._get_current_section_and_alpha()
        
        # 모든 섹션이 끝났으면 루프 또는 종료
        if section_idx >= len(self.credits_sections):
            # 종료 메시지 표시
            msg = "[ Z / Enter: 돌아가기 ]"
            console.print(
                (self.screen_width - len(msg)) // 2,
                self.screen_height // 2,
                msg,
                fg=(150, 150, 180)
            )
            return
        
        # 현재 섹션 렌더링
        section = self.credits_sections[section_idx]
        lines = section["lines"]
        
        # 중앙 위치 계산
        total_lines = len(lines)
        start_y = (self.screen_height - total_lines * 2) // 2
        
        for i, (text, base_color) in enumerate(lines):
            if not text:
                continue
            
            # 알파 적용된 색상
            faded_color = (
                int(base_color[0] * alpha),
                int(base_color[1] * alpha),
                int(base_color[2] * alpha)
            )
            
            # 텍스트 중앙 정렬
            x = (self.screen_width - len(text)) // 2
            y = start_y + i * 2
            
            # 첫 번째 줄(제목)은 살짝 펄스 효과
            if i == 0 and alpha > 0.5:
                pulse = 0.9 + 0.1 * math.sin(self.animation_frame / 15.0)
                faded_color = (
                    min(255, int(faded_color[0] * pulse)),
                    min(255, int(faded_color[1] * pulse)),
                    min(255, int(faded_color[2] * pulse))
                )
            
            console.print(x, y, text, fg=faded_color)
        
        # 하단 안내
        controls = "→/↓: 스킵  |  Z/Enter/X/ESC: 돌아가기"
        console.print(
            (self.screen_width - len(controls)) // 2,
            self.screen_height - 2,
            controls,
            fg=(60, 60, 80)
        )
        
        # 진행 표시 (섹션 번호)
        progress = f"[{section_idx + 1}/{len(self.credits_sections)}]"
        console.print(
            self.screen_width - len(progress) - 2,
            self.screen_height - 2,
            progress,
            fg=(60, 60, 80)
        )


def run_credits(console: tcod.console.Console, context: tcod.context.Context) -> None:
    """
    크레딧 화면 실행
    """
    # 크레딧 BGM 재생 (1회만, 루프 없음)
    try:
        from src.audio import play_bgm
        from src.audio.audio_manager import get_audio_manager
        play_bgm("credits", loop=False, fade_in=True)
    except Exception as e:
        pass  # BGM 재생 실패는 무시
    
    credits_ui = CreditsUI(console.width, console.height)
    
    # 프레임 관리
    last_time = time.time()
    frame_time = 1.0 / 30.0  # 30 FPS
    
    while not credits_ui.should_close:
        current_time = time.time()
        delta_time = current_time - last_time
        
        if delta_time >= frame_time:
            last_time = current_time
            
            # 렌더링
            credits_ui.render(console)
            context.present(console)
        
        # pygame 이벤트 업데이트
        try:
            import pygame
            pygame.event.pump()
        except:
            pass
        
        # 입력 처리
        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)
            
            if action:
                if credits_ui.handle_input(action):
                    # BGM 정지
                    try:
                        from src.audio.audio_manager import get_audio_manager
                        audio_manager = get_audio_manager()
                        audio_manager.stop_bgm(fade_out=True)
                    except:
                        pass
                    return
            
            if isinstance(event, tcod.event.Quit):
                # BGM 정지
                try:
                    from src.audio.audio_manager import get_audio_manager
                    audio_manager = get_audio_manager()
                    audio_manager.stop_bgm(fade_out=True)
                except:
                    pass
                return
        
        # 게임패드 입력
        gamepad_action = unified_input_handler.get_action()
        if gamepad_action:
            if credits_ui.handle_input(gamepad_action):
                # BGM 정지
                try:
                    from src.audio.audio_manager import get_audio_manager
                    audio_manager = get_audio_manager()
                    audio_manager.stop_bgm(fade_out=True)
                except:
                    pass
                return
        
        # CPU 사용률 낮추기
        time.sleep(0.01)
    
    # 종료 시 BGM 정지
    try:
        from src.audio.audio_manager import get_audio_manager
        audio_manager = get_audio_manager()
        audio_manager.stop_bgm(fade_out=True)
    except:
        pass

