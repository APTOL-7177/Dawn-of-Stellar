"""
LLM 매크로 - 화면을 보고 키보드를 누르는 AI 플레이어

실제 플레이어와 동일한 환경:
- 게임 내부 상태 접근 없음
- 화면 캡처로 시각 정보 획득
- 실제 키보드 입력으로 조작

Usage:
    python llm_macro.py
"""

import time
import base64
import json
import io
from pathlib import Path

# 화면 캡처
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.05
except ImportError:
    print("❌ pyautogui 필요: pip install pyautogui")
    exit(1)

try:
    from PIL import Image
except ImportError:
    print("❌ Pillow 필요: pip install Pillow")
    exit(1)

# LLM API
try:
    import requests
except ImportError:
    print("❌ requests 필요: pip install requests")
    exit(1)


class LLMMacro:
    """화면을 보고 키를 누르는 LLM 매크로"""
    
    # 게임 키 매핑
    KEYS = {
        'up': 'up',
        'down': 'down',
        'left': 'left',
        'right': 'right',
        'confirm': 'return',
        'cancel': 'escape',
        'wait': 'space',
        'inventory': 'i',
        'character': 'c',
    }
    
    def __init__(self, 
                 model: str = "llava:7b",
                 ollama_url: str = "http://localhost:11434",
                 capture_region: tuple = None,
                 action_delay: float = 0.3):
        """
        Args:
            model: 비전 LLM 모델 (llava, bakllava 등)
            ollama_url: Ollama 서버 URL
            capture_region: 캡처 영역 (x, y, width, height) - None이면 전체 화면
            action_delay: 행동 간 딜레이 (초)
        """
        self.model = model
        self.ollama_url = ollama_url
        self.capture_region = capture_region
        self.action_delay = action_delay
        self.running = False
        
        # 게임 상황 설명 (LLM에게 컨텍스트 제공)
        self.game_context = """
당신은 턴제 RPG 게임 "Dawn of Stellar"를 플레이하는 AI입니다.

게임 규칙:
- 탐험: 화살표 키로 이동, 계단(>)을 찾아 다음 층으로
- 전투: 메뉴에서 행동 선택 (BRV 공격 → HP 공격 순서)
- 목표: 던전 탐험, 적 처치, 생존

화면을 보고 다음 행동을 결정하세요.
응답 형식 (JSON만):
{"key": "up|down|left|right|confirm|cancel|wait", "reason": "간단한 이유"}
"""
    
    def capture_screen(self) -> Image.Image:
        """화면 캡처"""
        if self.capture_region:
            x, y, w, h = self.capture_region
            screenshot = pyautogui.screenshot(region=(x, y, w, h))
        else:
            screenshot = pyautogui.screenshot()
        return screenshot
    
    def image_to_base64(self, image: Image.Image) -> str:
        """이미지를 base64로 변환"""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def ask_llm(self, image: Image.Image, extra_context: str = "") -> dict:
        """비전 LLM에게 이미지를 보여주고 행동 결정"""
        img_base64 = self.image_to_base64(image)
        
        prompt = f"{self.game_context}\n{extra_context}\n\n화면을 보고 다음 행동을 JSON으로 응답하세요."
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [img_base64],
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 100,
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get('response', '')
                
                # JSON 추출
                try:
                    # JSON 블록 찾기
                    if '{' in text and '}' in text:
                        start = text.find('{')
                        end = text.rfind('}') + 1
                        json_str = text[start:end]
                        return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
                
                # 단순 키워드 매칭 폴백
                text_lower = text.lower()
                for key in self.KEYS:
                    if key in text_lower:
                        return {"key": key, "reason": text[:50]}
                
                return {"key": "wait", "reason": "파싱 실패"}
            else:
                print(f"❌ LLM 오류: {response.status_code}")
                return {"key": "wait", "reason": "API 오류"}
                
        except Exception as e:
            print(f"❌ LLM 요청 실패: {e}")
            return {"key": "wait", "reason": str(e)}
    
    def press_key(self, key_name: str):
        """실제 키 입력"""
        key = self.KEYS.get(key_name, key_name)
        try:
            pyautogui.press(key)
            print(f"⌨️ 키 입력: {key}")
        except Exception as e:
            print(f"❌ 키 입력 실패: {e}")
    
    def run_once(self) -> dict:
        """한 번의 행동 사이클"""
        # 1. 화면 캡처
        screenshot = self.capture_screen()
        
        # 2. LLM에게 질문
        action = self.ask_llm(screenshot)
        
        # 3. 키 입력
        key = action.get('key', 'wait')
        reason = action.get('reason', '')
        
        print(f"🤖 AI 결정: {key} - {reason}")
        self.press_key(key)
        
        return action
    
    def run(self, max_steps: int = None):
        """매크로 실행 루프"""
        print("=" * 50)
        print("🤖 LLM 매크로 시작!")
        print(f"모델: {self.model}")
        print(f"행동 딜레이: {self.action_delay}초")
        print("중지: Ctrl+C")
        print("=" * 50)
        
        self.running = True
        step = 0
        
        try:
            while self.running:
                if max_steps and step >= max_steps:
                    print(f"✅ {max_steps}스텝 완료")
                    break
                
                step += 1
                print(f"\n--- 스텝 {step} ---")
                
                self.run_once()
                time.sleep(self.action_delay)
                
        except KeyboardInterrupt:
            print("\n⏹️ 매크로 중지됨")
        finally:
            self.running = False
    
    def calibrate(self):
        """게임 창 영역 캘리브레이션"""
        print("🎯 게임 창 영역 설정")
        print("게임 창의 왼쪽 위 모서리로 마우스를 이동하고 Enter를 누르세요...")
        input()
        x1, y1 = pyautogui.position()
        print(f"왼쪽 위: ({x1}, {y1})")
        
        print("게임 창의 오른쪽 아래 모서리로 마우스를 이동하고 Enter를 누르세요...")
        input()
        x2, y2 = pyautogui.position()
        print(f"오른쪽 아래: ({x2}, {y2})")
        
        self.capture_region = (x1, y1, x2 - x1, y2 - y1)
        print(f"✅ 캡처 영역: {self.capture_region}")
        return self.capture_region


class SimpleLLMMacro(LLMMacro):
    """텍스트 기반 LLM 매크로 (비전 없이 OCR 또는 규칙 기반)"""
    
    def __init__(self, model: str = "qwen3:0.6b", **kwargs):
        super().__init__(model=model, **kwargs)
        self.last_screenshot = None
        self.step_count = 0
    
    def ask_llm(self, image: Image.Image, extra_context: str = "") -> dict:
        """간단한 규칙 기반 + 텍스트 LLM 하이브리드"""
        self.step_count += 1
        
        # 이미지 분석 (간단한 픽셀 비교)
        # 실제로는 OCR이나 비전 모델 사용 권장
        
        # 텍스트 LLM에게 상황 설명
        prompt = f"""
당신은 턴제 RPG를 플레이하는 AI입니다.
현재 스텝: {self.step_count}

다음 중 하나를 선택하세요:
- up/down/left/right: 이동
- confirm: 확인/선택/공격
- cancel: 취소/뒤로
- wait: 대기

JSON으로 응답: {{"key": "키이름", "reason": "이유"}}
"""
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.5, "num_predict": 50}
                },
                timeout=10
            )
            
            if response.status_code == 200:
                text = response.json().get('response', '')
                
                # JSON 추출
                if '{' in text:
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    try:
                        return json.loads(text[start:end])
                    except:
                        pass
                
                # 키워드 매칭
                for key in ['up', 'down', 'left', 'right', 'confirm', 'cancel']:
                    if key in text.lower():
                        return {"key": key, "reason": "키워드 매칭"}
            
        except Exception as e:
            print(f"LLM 오류: {e}")
        
        # 랜덤 폴백
        import random
        return {"key": random.choice(['up', 'down', 'left', 'right', 'confirm']), 
                "reason": "랜덤 폴백"}


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM 매크로 - 화면을 보고 키를 누르는 AI")
    parser.add_argument('--model', default='llava:7b', help='비전 LLM 모델 (llava, bakllava)')
    parser.add_argument('--simple', action='store_true', help='텍스트 LLM 모드 (비전 없음)')
    parser.add_argument('--delay', type=float, default=0.5, help='행동 간 딜레이 (초)')
    parser.add_argument('--steps', type=int, default=None, help='최대 스텝 수')
    parser.add_argument('--calibrate', action='store_true', help='게임 창 영역 설정')
    
    args = parser.parse_args()
    
    if args.simple:
        macro = SimpleLLMMacro(model='qwen3:0.6b', action_delay=args.delay)
        print("📝 텍스트 LLM 모드 (비전 없음)")
    else:
        macro = LLMMacro(model=args.model, action_delay=args.delay)
        print(f"👁️ 비전 LLM 모드: {args.model}")
    
    if args.calibrate:
        macro.calibrate()
    
    print("\n3초 후 시작... 게임 창을 활성화하세요!")
    time.sleep(3)
    
    macro.run(max_steps=args.steps)


if __name__ == "__main__":
    main()
