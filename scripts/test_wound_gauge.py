"""
HP 게이지 상처 표시 테스트 스크립트

다양한 HP/상처 조합으로 게이지 렌더링을 직접 확인
"""

import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tcod
import tcod.event
from src.ui.gauge_tileset import initialize_gauge_tiles, get_gauge_tile_manager
from src.ui.gauge_renderer import GaugeRenderer

# 화면 크기
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 40

# 테스트 케이스들 - (이름, current_hp, max_hp, wound_damage, 테스트용_셀수)
TEST_CASES = [
    # 기본 케이스
    ("상처 없음 (HP 100%)", 100, 100, 0, None),
    ("상처 없음 (HP 50%)", 50, 100, 0, None),
    ("상처 없음 (HP 20%)", 20, 100, 0, None),
    # 상처 20%
    ("상처 20% (HP 80%)", 80, 100, 20, None),
    ("상처 20% (HP 50%)", 50, 100, 20, None),
    ("상처 20% (HP 20%)", 20, 100, 20, None),
    # 상처 50%
    ("상처 50% (HP 50%)", 50, 100, 50, None),
    ("상처 50% (HP 30%)", 30, 100, 50, None),
    # 상처 30%
    ("상처 30% (HP 70%)", 70, 100, 30, None),
    # 기타
    ("상처 10% (HP 90%)", 90, 100, 10, None),
    ("상처 80% (HP 20%)", 20, 100, 80, None),
    ("상처 20% (HP 79%)", 79, 100, 20, None),
    # 문제 케이스들 - 15셀
    ("15셀 W30% HP70%", 70, 100, 30, 15),
    ("15셀 W50% HP30%", 30, 100, 50, 15),
    ("15셀 W50% HP50%", 50, 100, 50, 15),
    # 문제 케이스들 - 12셀
    ("12셀 W20% HP50%", 50, 100, 20, 12),
    ("12셀 W20% HP20%", 20, 100, 20, 12),
    ("12셀 W20% HP80%", 80, 100, 20, 12),
]


def main():
    """메인 테스트 함수"""
    # 폰트 로드 (프로젝트 루트에서 찾기)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # BDF 폰트 우선 검색
    bdf_path = os.path.join(project_root, "GalmuriMono9.bdf")
    
    if os.path.exists(bdf_path):
        print(f"BDF 폰트 사용: {bdf_path}")
        tileset = tcod.tileset.load_bdf(bdf_path)
    else:
        # TTF 폰트 폴백
        font_candidates = [
            os.path.join(project_root, "dalmoori.ttf"),
            os.path.join(project_root, "D2Coding.ttf"),
            os.path.join(project_root, "GalmuriMono9.ttf"),
        ]
        
        font_path = None
        for candidate in font_candidates:
            if os.path.exists(candidate):
                font_path = candidate
                break
        
        if font_path is None:
            print(f"폰트를 찾을 수 없습니다. 프로젝트 루트에 bdf 또는 ttf 파일이 필요합니다.")
            print(f"검색 경로: {project_root}")
            return
        
        print(f"TTF 폰트 사용: {font_path}")
        tileset = tcod.tileset.load_truetype_font(font_path, 16, 16)
    
    # 게이지 타일 초기화
    initialize_gauge_tiles(tileset)
    
    # 콘솔 생성
    console = tcod.console.Console(SCREEN_WIDTH, SCREEN_HEIGHT)
    
    # 컨텍스트 생성 (실제 게임과 동일한 렌더러 사용)
    # config.yaml에서 렌더러 설정 읽기
    renderer_name = "opengl2"  # 기본값 (실제 게임과 동일)
    try:
        import yaml
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                renderer_name = config.get("display", {}).get("renderer", "opengl2")
    except Exception:
        pass  # 설정을 읽지 못하면 기본값 사용
    
    renderer_map = {
        "sdl2": tcod.context.RENDERER_SDL2,
        "opengl": tcod.context.RENDERER_OPENGL,
        "opengl2": tcod.context.RENDERER_OPENGL2,
        "auto": None  # TCOD가 자동 선택
    }
    renderer = renderer_map.get(renderer_name.lower(), None)
    
    with tcod.context.new(
        columns=SCREEN_WIDTH,
        rows=SCREEN_HEIGHT,
        tileset=tileset,
        title="HP 게이지 상처 표시 테스트",
        vsync=True,
        renderer=renderer,
    ) as context:
        
        gauge_renderer = GaugeRenderer()
        selected_case = 0
        
        while True:
            # 화면 클리어
            console.clear()
            
            # 타이틀
            console.print(2, 1, "═" * 76, fg=(100, 100, 150))
            console.print(2, 2, "  HP 게이지 상처(Wound) 표시 테스트", fg=(255, 255, 100))
            console.print(2, 3, "  [↑/↓] 케이스 선택  [Q] 종료", fg=(150, 150, 150))
            console.print(2, 4, "═" * 76, fg=(100, 100, 150))
            
            # 현재 선택된 테스트 케이스 정보
            name, current_hp, max_hp, wound, test_width = TEST_CASES[selected_case]
            effective_max = max_hp - wound
            hp_percent = (current_hp / max_hp) * 100
            wound_percent = (wound / max_hp) * 100
            
            console.print(4, 6, f"▶ 테스트 케이스: {name}", fg=(100, 255, 100))
            console.print(4, 7, f"  현재 HP: {current_hp}/{max_hp} ({hp_percent:.0f}%)", fg=(200, 200, 200))
            console.print(4, 8, f"  상처량: {wound} ({wound_percent:.0f}%)", fg=(200, 100, 100))
            console.print(4, 9, f"  유효 최대 HP: {effective_max}", fg=(200, 200, 100))
            
            # 특정 셀 수 테스트인 경우
            if test_width:
                console.print(4, 12, f"게이지 (너비 {test_width} - 문제 케이스):", fg=(255, 150, 150))
                console.print(4, 13, "HP:", fg=(200, 200, 200))
                entity_id = f"test_{selected_case}_target"
                gauge_renderer.render_animated_hp_bar(
                    console, 8, 13, test_width,
                    current_hp, max_hp, entity_id,
                    wound_damage=wound, show_numbers=True
                )
            else:
                # 큰 게이지 (너비 30)
                console.print(4, 12, "게이지 (너비 30):", fg=(150, 150, 200))
                console.print(4, 13, "HP:", fg=(200, 200, 200))
                entity_id = f"test_{selected_case}_large"
                gauge_renderer.render_animated_hp_bar(
                    console, 8, 13, 30,
                    current_hp, max_hp, entity_id,
                    wound_damage=wound, show_numbers=True
                )
            
            # 15셀 게이지
            console.print(4, 15, "게이지 (너비 15):", fg=(150, 150, 200))
            console.print(4, 16, "HP:", fg=(200, 200, 200))
            entity_id = f"test_{selected_case}_15cell"
            gauge_renderer.render_animated_hp_bar(
                console, 8, 16, 15,
                current_hp, max_hp, entity_id,
                wound_damage=wound, show_numbers=True
            )
            
            # 12셀 게이지
            console.print(4, 18, "게이지 (너비 12):", fg=(150, 150, 200))
            console.print(4, 19, "HP:", fg=(200, 200, 200))
            entity_id = f"test_{selected_case}_12cell"
            gauge_renderer.render_animated_hp_bar(
                console, 8, 19, 12,
                current_hp, max_hp, entity_id,
                wound_damage=wound, show_numbers=True
            )
            
            # 모든 테스트 케이스 미리보기
            console.print(4, 22, "─" * 40, fg=(80, 80, 80))
            console.print(4, 23, "모든 테스트 케이스:", fg=(150, 150, 200))
            
            for i, (case_name, hp, max_hp_val, wound_val, _) in enumerate(TEST_CASES):
                y = 25 + i
                if y >= SCREEN_HEIGHT - 2:
                    break
                    
                # 선택 표시
                if i == selected_case:
                    console.print(2, y, "▶", fg=(255, 255, 100))
                else:
                    console.print(2, y, " ", fg=(100, 100, 100))
                
                # 케이스 이름 (짧게)
                short_name = case_name[:18].ljust(18)
                color = (255, 255, 255) if i == selected_case else (150, 150, 150)
                console.print(4, y, short_name, fg=color)
                
                # 미니 게이지
                mini_entity_id = f"mini_{i}"
                gauge_renderer.render_animated_hp_bar(
                    console, 24, y, 12,
                    hp, max_hp_val, mini_entity_id,
                    wound_damage=wound_val, show_numbers=False
                )
                
                # HP/상처 정보
                info = f"{hp}/{max_hp_val} W:{wound_val}"
                console.print(38, y, info, fg=(120, 120, 120))
            
            # 범례
            console.print(55, 6, "[ 범례 ]", fg=(200, 200, 100))
            console.draw_rect(55, 8, 3, 1, ord(" "), bg=(50, 220, 50))
            console.print(59, 8, "= 현재 HP", fg=(150, 150, 150))
            console.draw_rect(55, 9, 3, 1, ord(" "), bg=(80, 30, 50))
            console.print(59, 9, "= 상처 영역 (빗금)", fg=(150, 150, 150))
            console.draw_rect(55, 10, 3, 1, ord(" "), bg=(20, 80, 20))
            console.print(59, 10, "= 빈 HP 영역", fg=(150, 150, 150))
            console.print(55, 11, "┃", fg=(200, 80, 100))
            console.print(57, 11, "= 상처 시작 마커", fg=(150, 150, 150))
            
            # 화면 출력
            context.present(console)
            
            # 이벤트 처리
            for event in tcod.event.wait():
                if isinstance(event, tcod.event.Quit):
                    return
                elif isinstance(event, tcod.event.KeyDown):
                    if event.sym == tcod.event.KeySym.q or event.sym == tcod.event.KeySym.ESCAPE:
                        return
                    elif event.sym == tcod.event.KeySym.UP:
                        selected_case = (selected_case - 1) % len(TEST_CASES)
                    elif event.sym == tcod.event.KeySym.DOWN:
                        selected_case = (selected_case + 1) % len(TEST_CASES)


if __name__ == "__main__":
    main()

