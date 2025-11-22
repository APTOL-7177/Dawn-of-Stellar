import tcod
from typing import List, Tuple

class BotHelpUI:
    """봇 명령어 도움말 UI"""
    
    def __init__(self, width: int = 60, height: int = 40):
        self.width = width
        self.height = height
        self.is_visible = False
        
    def toggle(self):
        """보이기/숨기기 토글"""
        self.is_visible = not self.is_visible
        
    def draw(self, console: tcod.console.Console):
        """도움말 창 그리기"""
        if not self.is_visible:
            return
            
        # 화면 중앙 좌표 계산
        screen_width = console.width
        screen_height = console.height
        x = (screen_width - self.width) // 2
        y = (screen_height - self.height) // 2
        
        # 창 프레임 그리기
        console.draw_frame(
            x, y, self.width, self.height,
            title=" 봇 명령어 도움말 (Bot Commands) ",
            clear=True,
            fg=(255, 255, 255),
            bg=(10, 10, 20)
        )
        
        # 도움말 내용
        commands = [
            ("1", "도움말", "이 도움말 창을 엽니다."),
            ("2", "아이템 확인", "봇의 인벤토리를 확인합니다."),
            ("3", "아이템 요청", "봇에게 아이템 공유를 요청합니다."),
            ("4", "골드 요청", "봇에게 골드 공유를 요청합니다."),
            ("5", "탐험 모드", "봇이 자유롭게 맵을 탐험하며 파밍합니다."),
            ("6", "따라오기", "봇이 플레이어를 따라다닙니다."),
            ("7", "전투 회피", "전투 회피 모드를 켜거나 끕니다."),
            ("8", "파밍 이동", "이동 경로상의 자원을 적극적으로 채집합니다."),
            ("9", "위치 공유", "봇이 현재 위치를 채팅으로 알립니다."),
            ("0", "대기", "봇이 현재 위치에서 대기합니다.")
        ]
        
        # 내용 출력
        content_y = y + 2
        
        console.print(x + 2, content_y, "숫자 키를 눌러 봇에게 명령을 내릴 수 있습니다.", fg=(200, 200, 200))
        content_y += 2
        
        for key, name, desc in commands:
            # 키 (노란색)
            console.print(x + 2, content_y, f"[{key}]", fg=(255, 255, 0))
            # 이름 (청록색)
            console.print(x + 6, content_y, f"{name}:", fg=(0, 255, 255))
            # 설명 (흰색)
            console.print(x + 20, content_y, desc, fg=(220, 220, 220))
            content_y += 2
            
        # 하단 안내
        console.print(
            x + self.width // 2, 
            y + self.height - 2, 
            "닫으려면 [ESC] 또는 [1] 키를 누르세요.", 
            fg=(150, 150, 150),
            alignment=tcod.CENTER
        )

    def handle_input(self, event: tcod.event.Event) -> bool:
        """입력 처리 (True 반환 시 UI 닫힘)"""
        if not self.is_visible:
            return False
            
        if isinstance(event, tcod.event.KeyDown):
            if event.sym == tcod.event.K_ESCAPE or event.sym == tcod.event.K_1:
                self.toggle()
                return True
                
        return False

