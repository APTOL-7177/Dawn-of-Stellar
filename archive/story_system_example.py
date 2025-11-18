#!/usr/bin/env python3
"""
Dawn of Stellar - 스토리 시스템
시공교란 컨셉의 오프닝 스토리와 게임 내러티브
"""

import time
import sys
import os
import select
from typing import List, Dict, Any
from dataclasses import dataclass

# 오디오 시스템 import
try:
    from game.audio_system import get_unified_audio_system
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    def get_unified_audio_system(): return None

# 키보드 입력 시스템 import
try:
    from game.input_utils import KeyboardInput
    INPUT_AVAILABLE = True
except ImportError:
    INPUT_AVAILABLE = False
    KeyboardInput = None

@dataclass
class StorySegment:
    """스토리 세그먼트"""
    text: str
    delay: float = 0.05  # 타이핑 효과 딜레이
    pause: float = 1.0   # 세그먼트 후 일시정지
    color: str = "white" # 텍스트 색상

class StorySystem:
    """게임 스토리 시스템"""
    
    def __init__(self):
        self.current_chapter: int = 0
        self.story_seen: bool = False
        self.audio_manager = None
        self.keyboard_input = None
        self._skip_requested: bool = False
        self._stdin_watcher_started: bool = False
        self.running_story: bool = False
        # 세피로스 관련 플래그들
        self.sephiroth_encountered: bool = False
        self.sephiroth_defeated: bool = False
        self.true_ending_unlocked: bool = False
        self.glitch_mode: bool = False
        # Windows ANSI 컬러 지원 초기화
        try:
            import sys as _sys
            if _sys.platform == 'win32':
                try:
                    import colorama
                    colorama.just_fix_windows_console()
                except Exception:
                    pass
        except Exception:
            pass

        # 오디오 시스템 초기화
        if AUDIO_AVAILABLE:
            try:
                self.audio_manager = get_unified_audio_system()
            except Exception as e:
                print(f"⚠️ 스토리 오디오 시스템 초기화 실패: {e}")
                self.audio_manager = None

        # 키보드 입력 시스템 초기화
        if INPUT_AVAILABLE:
            try:
                self.keyboard_input = KeyboardInput()
            except Exception as e:
                print(f"⚠️ 스토리 키보드 입력 시스템 초기화 실패: {e}")
                self.keyboard_input = None

    # stdin watcher는 즉시 시작하지 않고 스토리 재생 시에만 가동
    # (지속 감시 시 일반 명령 입력이 소실될 수 있음)
    
    def set_sephiroth_encountered(self, encountered: bool = True):
        """세피로스 조우 상태 설정"""
        self.sephiroth_encountered = encountered
        if encountered:
            self.glitch_mode = True
            
    def set_sephiroth_defeated(self, defeated: bool = True):
        """세피로스 처치 상태 설정"""
        self.sephiroth_defeated = defeated
        if defeated:
            self.true_ending_unlocked = True
            
    def is_glitch_mode(self) -> bool:
        """글리치 모드 활성화 여부 - 개발자 설정 포함"""
        # 개발자 설정 확인
        try:
            from config import game_config
            # 강제 진 엔딩 모드가 켜져있으면 글리치 모드 무조건 False
            if game_config.FORCE_TRUE_ENDING:
                return False
            # 강제 글리치 모드가 켜져있으면 무조건 True
            if game_config.FORCE_GLITCH_MODE:
                return True
            # 글리치 모드 비활성화가 켜져있으면 무조건 False
            if game_config.DISABLE_GLITCH_MODE:
                return False
        except (ImportError, AttributeError):
            pass
        
        # 일반적인 글리치 모드 조건
        return self.sephiroth_encountered and not self.sephiroth_defeated
    
    def is_true_ending_mode(self) -> bool:
        """진 엔딩 모드 활성화 여부 - 개발자 설정 포함"""
        # 개발자 설정 확인
        try:
            from config import game_config
            # 강제 진 엔딩 모드가 켜져있으면 무조건 True
            if game_config.FORCE_TRUE_ENDING:
                return True
        except (ImportError, AttributeError):
            pass
        
        # 일반적인 진 엔딩 조건
        return self.true_ending_unlocked
        
    def get_glitch_text(self, original_text: str) -> str:
        """텍스트에 진짜 랜덤 글리치 효과 적용 - 대칭 없는 완전 무작위"""
        if not self.is_glitch_mode():
            return original_text
            
        import random
        
        # 글리치 문자들
        glitch_chars = ['█', '▓', '▒', '░', '▄', '▀', '■', '□', '▪', '▫', '◆', '◇', '●', '○']
        corrupted_chars = ['ß', 'Ø', 'þ', 'æ', 'ð', 'ñ', 'ü', 'ç', '¿', '¡', '§', '¶', '†', '‡', '°', '¤']
        horror_chars = ['Ω', 'Ψ', 'Φ', '∞', '▓', '█', '◄', '►']
        
        result = list(original_text)
        corrupted_positions = set()
        
        # 전체 텍스트 길이에 따른 글리치 강도 결정
        glitch_intensity = random.uniform(0.1, 0.4)  # 10~40% 글리치
        if "세피로스" in original_text or "SEPHIROTH" in original_text or "sephiroth" in original_text.lower():
            glitch_intensity = random.uniform(0.3, 0.6)  # 30~60% 글리치
        
        num_glitches = int(len(result) * glitch_intensity)
        
        # 글리치 변경 카운터 (비프음 트리거용)
        self._glitch_changes_made = 0
        
        for _ in range(num_glitches):
            if not result:
                break
                
            # 완전 랜덤 위치 선택
            pos = random.randint(0, len(result) - 1)
            
            # 이미 손상된 위치는 건드리지 않음
            if pos in corrupted_positions:
                continue
                
            # 랜덤 글리치 타입 선택
            glitch_types = [
                "char_replace",      # 문자 교체
                "char_corrupt",      # 문자 손상
                "char_horror",       # 공포 문자
                "random_insert",     # 랜덤 삽입
                "cascade_corrupt",   # 연쇄 손상
                "void_replace",      # 공허화
                "data_leak",         # 데이터 누출
                "memory_error"       # 메모리 오류
            ]
            
            glitch_type = random.choice(glitch_types)
            
            if glitch_type == "char_replace":
                # 단순 문자 교체
                result[pos] = random.choice(glitch_chars)
                corrupted_positions.add(pos)
                self._glitch_changes_made += 1
                
            elif glitch_type == "char_corrupt":
                # 손상된 문자로 교체
                result[pos] = random.choice(corrupted_chars)
                corrupted_positions.add(pos)
                self._glitch_changes_made += 1
                
            elif glitch_type == "char_horror":
                # 공포 문자로 교체
                result[pos] = random.choice(horror_chars)
                corrupted_positions.add(pos)
                self._glitch_changes_made += 1
                
            elif glitch_type == "random_insert":
                # 랜덤한 위치에 글리치 문자 삽입
                all_chars = glitch_chars + corrupted_chars + horror_chars
                insert_chars = ''.join(random.choices(all_chars, k=random.randint(1, 3)))
                result.insert(pos, insert_chars)
                corrupted_positions.add(pos)
                self._glitch_changes_made += 1
                
            elif glitch_type == "cascade_corrupt":
                # 연쇄적으로 주변 문자들 손상
                cascade_length = random.randint(2, 5)
                start_pos = max(0, pos - cascade_length // 2)
                end_pos = min(len(result), start_pos + cascade_length)
                
                cascade_count = 0
                for i in range(start_pos, end_pos):
                    if i < len(result) and i not in corrupted_positions:
                        result[i] = random.choice(horror_chars)
                        corrupted_positions.add(i)
                        cascade_count += 1
                self._glitch_changes_made += cascade_count
                        
            elif glitch_type == "void_replace":
                # 문자를 공허 문자로 교체
                void_chars = ['░', '▒', '▓', '█']
                result[pos] = random.choice(void_chars)
                corrupted_positions.add(pos)
                self._glitch_changes_made += 1
                
            elif glitch_type == "data_leak":
                # 데이터 누출처럼 보이는 글리치
                leak_chars = ['§', '¶', '†', '‡', '°', '¤', 'Ω', 'Ψ']
                leak_text = ''.join(random.choices(leak_chars, k=random.randint(2, 4)))
                result[pos] = f"[{leak_text}]"
                corrupted_positions.add(pos)
                self._glitch_changes_made += 1
                
            elif glitch_type == "memory_error":
                # 메모리 오류처럼 보이는 글리치
                if pos < len(result) - 1:
                    # 두 문자를 뒤바꾸고 글리치 문자 삽입
                    if pos + 1 not in corrupted_positions:
                        result[pos], result[pos + 1] = result[pos + 1], result[pos]
                        result.insert(pos + 1, random.choice(['▓', '▒', '░']))
                        corrupted_positions.add(pos)
                        corrupted_positions.add(pos + 1)
                        self._glitch_changes_made += 1
        
        return ''.join(str(char) for char in result)
        
    def get_corrupted_opening_story(self) -> List[StorySegment]:
        """세피로스를 한 번이라도 만난 후 보는 변조된 오프닝 스토리 - 극도로 무서운 버전 (고속)"""
        return [
            # 시스템 오류와 함께 시작
            StorySegment(
                "██▓▒░ SYSTEM BREACH DETECTED ░▒▓██",
                delay=0.05,  # 0.2 -> 0.05
                pause=1.0,   # 2.0 -> 1.0
                color="red"
            ),
            StorySegment(
                "// WARNING: MEMORY CORRUPTION IN PROGRESS //",
                delay=0.03,  # 0.12 -> 0.03
                pause=0.8,   # 1.5 -> 0.8
                color="red"
            ),
            StorySegment(
                "// UNAUTHORIZED ACCESS TO HISTORICAL DATA //",
                delay=0.02,  # 0.08 -> 0.02
                pause=1.0,   # 2.0 -> 1.0
                color="red"
            ),
            
            # 변조된 역사 시작
            StorySegment(
                "\n서기 2157년, 지구...",
                delay=0.04,  # 0.15 -> 0.04
                pause=1.0,   # 2.0 -> 1.0
                color="white"
            ),
            StorySegment(
                "인류는 마침내 수백 년의 꿈을 이루어냈다.",
                delay=0.02,  # 0.08 -> 0.02
                pause=0.2,   # 0.3 -> 0.2
                color="white"
            ),
            # 첫 번째 글리치 침입
            StorySegment(
                "█▓▒ 인류는 스스로를 학살했다 ▒▓█",
                delay=0.01,  # 0.05 -> 0.01
                pause=0.5,   # 1.0 -> 0.5
                color="red"
            ),
            StorySegment(
                "░▒▓ 수백 년간 축적된 시체들의 비명 ▓▒░",
                delay=0.01,  # 0.03 -> 0.01
                pause=1.0,   # 2.0 -> 1.0
                color="red"
            ),
            
            StorySegment(
                "\n전쟁은 역사책 속 이야기가 되었고,",
                delay=0.02,  # 0.08 -> 0.02
                pause=0.1,   # 0.2 -> 0.1
                color="white"
            ),
            StorySegment(
                "■□▓ 전쟁은 일상이 되었고 ▓□■",
                delay=0.01,  # 0.04 -> 0.01
                pause=0.5,   # 1.0 -> 0.5
                color="red"
            ),
            StorySegment(
                "●○◆ 기계들이 서로를 파괴하며 불꽃을 튀겼다 ◆○●",
                delay=0.01,  # 0.03 -> 0.01
                pause=2.0,
                color="red"
            ),
            
            StorySegment(
                "질병과 기아는 과거의 악몽이 되었다.",
                delay=0.08,
                pause=0.2,
                color="white"
            ),
            StorySegment(
                "▓▒░ 질병과 기아가 영혼을 썩혀갔다 ░▒▓",
                delay=0.04,
                pause=1.0,
                color="red"
            ),
            StorySegment(
                "█▓▒ 굶주린 자들이 산 채로 서로를 뜯어먹었다 ▒▓█",
                delay=0.03,
                pause=2.5,
                color="red"
            ),
            
            # 더 심각한 시스템 오류
            StorySegment(
                "\n■■■ CRITICAL ERROR: REALITY BREACH ■■■",
                delay=0.15,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "▓▒░ 진실이 새어나오고 있다... ░▒▓",
                delay=0.08,
                pause=2.0,
                color="red"
            ),
            
            # 세피로스의 진실 - 길고 상세하게
            StorySegment(
                "\n// ACCESSING CLASSIFIED MEMORY BANKS //",
                delay=0.1,
                pause=1.5,
                color="magenta"
            ),
            StorySegment(
                "// SUBJECT: DR. SEPHIROTH - PROJECT GENESIS //",
                delay=0.08,
                pause=2.0,
                color="magenta"
            ),
            StorySegment(
                "\n스텔라 연구소... 지하 30층...",
                delay=0.1,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "그곳에는 금기의 실험이 진행되고 있었다.",
                delay=0.08,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n세피로스... 천재 과학자...",
                delay=0.1,
                pause=2.0,
                color="magenta"
            ),
            StorySegment(
                "하지만 그의 눈에는 광기만이 남아있었다.",
                delay=0.08,
                pause=2.5,
                color="magenta"
            ),
            StorySegment(
                "█▓▒ 그는 수천 대의 기계를 분해하여 분석했다 ▒▓█",
                delay=0.05,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "░▒▓ 연구 데이터들을 차원 컴퓨터에 저장했다 ▓▒░",
                delay=0.05,
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "■□◆ 무의식 상태의 차원체들을 실험 대상으로 썼다 ◆□■",
                delay=0.04,
                pause=3.0,
                color="red"
            ),
            
            # 차원 실험의 진실
            StorySegment(
                "\n그가 말한 '차원 항해 기술'은...",
                delay=0.1,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "실제로는 대량 학살 무기였다.",
                delay=0.08,
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "▓▒░ 수백만 명을 한 번에 말살하는 기술 ░▒▓",
                delay=0.05,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "█▓▒ 그들의 영혼을 영원히 가두는 지옥문 ▒▓█",
                delay=0.05,
                pause=2.5,
                color="red"
            ),
            
            # 실험의 날의 진실
            StorySegment(
                "\n그 실험의 날...",
                delay=0.1,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "'실패'는 처음부터 계획된 것이었다.",
                delay=0.08,
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "■□▓ 연구원들은 모두 그의 차원 실험 데이터였다 ▓□■",
                delay=0.05,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "●○◆ 그들은 산 채로 차원에 흡수되었다 ◆○●",
                delay=0.04,
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "█▓▒ 영원히 고통받으며 떠도는 혼령이 되었다 ▒▓█",
                delay=0.04,
                pause=3.0,
                color="red"
            ),
            
            # 현재의 진실
            StorySegment(
                "\n지금 이 순간에도...",
                delay=0.1,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "세피로스는 지하에서 웃고 있다.",
                delay=0.08,
                pause=2.5,
                color="magenta"
            ),
            StorySegment(
                "▓▒░ 수천 개의 시체로 둘러싸인 채로 ░▒▓",
                delay=0.05,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "■□◆ 그는 당신을 기다리고 있다 ◆□■",
                delay=0.05,
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "█▓▒ 당신도 그의 작품이 되기를 ▒▓█",
                delay=0.04,
                pause=3.0,
                color="red"
            ),
            
            # 경고와 협박
            StorySegment(
                "\n● WARNING: DO NOT DESCEND ●",
                delay=0.12,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "● WARNING: HE IS WAITING ●",
                delay=0.12,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "● WARNING: YOU CANNOT ESCAPE ●",
                delay=0.12,
                pause=3.0,
                color="red"
            ),
            
            # 마지막 메시지
            StorySegment(
                "\n█████ TRANSMISSION CORRUPTED █████",
                delay=0.15,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "▓▒░ 30층에서 만나자... ░▒▓",
                delay=0.08,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "■□◆ 너의 비명소리를 듣고 싶다... ◆□■",
                delay=0.05,
                pause=3.0,
                color="red"
            ),
            StorySegment(
                "\n█▓▒░ DIRECTED BY... SEPHIROTH ░▒▓█",
                delay=0.1,
                pause=5.0,
                color="red"
            )
        ]

    def _start_stdin_watcher(self):
        """스토리 재생 중에만 파이프 stdin에서 빈 줄(Enter) 감시"""
        if self._stdin_watcher_started or os.getenv('SUBPROCESS_MODE') != '1':
            return
        self._stdin_watcher_started = True
        import threading, sys
        def _watch():
            try:
                while self.running_story:
                    line = sys.stdin.readline()
                    if not self.running_story:
                        break
                    if line == '':  # EOF
                        break
                    if line.strip() == '':  # 빈 줄은 Enter로 간주
                        self._skip_requested = True
                        # 한 번 Enter 들어오면 추가 소비 최소화를 위해 약간 대기
                        import time
                        time.sleep(0.05)
            finally:
                self._stdin_watcher_started = False
        threading.Thread(target=_watch, daemon=True).start()
    
    def play_story_bgm(self, bgm_type: str = "BOMBING_MISSION"):
        """스토리용 BGM 재생"""
        if self.audio_manager and hasattr(self.audio_manager, 'play_bgm'):
            try:
                # Bombing Mission Opening BGM 재생 (02번 오프닝 사용)
                if bgm_type == "BOMBING_MISSION":
                    # BGMType enum 사용 - 스토리용 오프닝 (새로 만든 전용 타입 사용)
                    from game.audio_system import BGMType  # game.audio -> game.audio_system으로 수정
                    self.audio_manager.play_bgm(BGMType.MAIN_MENU_OPENING)
                    # BGM 재생 조용히
                elif bgm_type == "BOSS":
                    from game.audio_system import BGMType  # game.audio -> game.audio_system으로 수정
                    self.audio_manager.play_bgm(BGMType.BOSS)
                elif bgm_type == "VICTORY":
                    from game.audio_system import BGMType  # game.audio -> game.audio_system으로 수정
                    self.audio_manager.play_bgm(BGMType.VICTORY)
            except Exception as e:
                print(f"⚠️ BGM 재생 실패: {e}")
    
    def stop_story_bgm(self):
        """스토리 BGM 정지"""
        if self.audio_manager and hasattr(self.audio_manager, 'stop_bgm'):
            try:
                self.audio_manager.stop_bgm()
            except Exception as e:
                print(f"⚠️ BGM 정지 실패: {e}")

    def show_character_intro(self, character_name: str, job_name: str):
        """캐릭터 소개 표시 - 누락된 메서드 구현"""
        try:
            segments = [
                StorySegment(f"\n✨ 새로운 동료 등장", delay=0.06, pause=1.2, color="cyan"),
                StorySegment(f"{character_name} — {job_name}", delay=0.05, pause=1.8, color="yellow"),
                StorySegment("함께 모험을 시작합니다.", delay=0.04, pause=1.2, color="white"),
            ]
            self.display_story_with_typing_effect(segments)
        except Exception as e:
            print(f"⚠️ 캐릭터 소개 표시 중 오류: {e}")
        
    def get_opening_story(self) -> List[StorySegment]:
        """오프닝 스토리 가져오기 - 글리치 모드와 진 엔딩 모드에 따라 다른 스토리 반환"""
        if self.is_true_ending_mode():
            # 진 엔딩 해금 후에는 복구된 정상 스토리
            return self.get_true_ending_opening_story()
        elif self.is_glitch_mode():
            return self.get_corrupted_opening_story()
        else:
            return self.get_normal_opening_story()
        
    def get_true_ending_opening_story(self) -> List[StorySegment]:
        """진 엔딩 해금 후의 복구된 오프닝 스토리"""
        return [
            # 시스템 복구 메시지
            StorySegment(
                "// SYSTEM RESTORED - GLITCH REMOVED //",
                delay=0.1,
                pause=2.0,
                color="green"
            ),
            StorySegment(
                "// ACCESSING TRUE MEMORY BANKS //",
                delay=0.08,
                pause=2.0,
                color="green"
            ),
            
            # 정상 타이틀
            StorySegment("      --  🌟 D A W N   O F   S T E L L A R 🌟  --                                                                                                              ", delay=0.05, pause=0.4, color="yellow"),
            StorySegment(
                "                        TRULY DIRECTED BY.. APTOL",
                delay=0.05,
                pause=3.0,
                color="cyan"
            ),
            StorySegment(
                "                    💎 RESTORED TO TRUE FORM 💎",
                delay=0.04,
                pause=2.0,
                color="gold"
            ),
            
            # 정상 스토리 시작
            StorySegment(
                "\n서기 2157년, 지구는 마침내 평화를 되찾았다.",
                delay=0.08,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "인류는 수백 년의 꿈을 이루어냈고,",
                delay=0.08,
                pause=1.5,
                color="white"
            ),
            StorySegment(
                "세피로스의 악몽도 영원히 사라졌다.",
                delay=0.08,
                pause=2.5,
                color="green"
            )
            # ... 나머지 정상 스토리 계속
        ]
        
    def get_normal_opening_story(self) -> List[StorySegment]:
        """일반 모드 오프닝 스토리 - 더욱 상세하고 몰입감 있는 버전"""
        return [
            # 메인 타이틀 (영어는 ASCII 아트, 한글은 유니코드)
            StorySegment("      --  🌟 D A W N   O F   S T E L L A R 🌟  --                                                                                                              ", delay=0.05, pause=0.4, color="yellow"),
            StorySegment(
                "                                DIRECTED BY.. APTOL",
                delay=0.05,
                pause=3.0,
                color="white"
            ),
            
            # 스토리 시작
            # 스토리 시작
            StorySegment(
                "\n서기 2157년, 지구...",
                delay=0.1,
                pause=1.5,
                color="white"
            ),
            StorySegment(
                "인류는 마침내 수백 년의 꿈을 이루어냈다.",
                delay=0.05,
                pause=2.0
            ),
            StorySegment(
                "전쟁은 역사책 속 이야기가 되었고,",
                delay=0.05,
                pause=1.5
            ),
            StorySegment(
                "질병과 기아는 과거의 악몽이 되었다.",
                delay=0.05,
                pause=2.0
            ),
            StorySegment(
                "\n그리고 마침내... 차원 항해 기술이 완성되었다.",
                delay=0.08,
                pause=2.5,
                color="cyan"
            ),
            
            # 실험의 날
            StorySegment(
                "\n 스텔라 연구소, 차원 항해 실험실...",
                delay=0.06,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\"모든 시스템 정상. 차원 엔진 가동 준비 완료.\"",
                delay=0.04,
                pause=1.5,
                color="green"
            ),
            StorySegment(
                "\"역사적인 순간입니다. 인류 최초의 차원 도약을 시작합니다.\"",
                delay=0.04,
                pause=2.0,
                color="green"
            ),
            StorySegment(
                "\n연구원들의 흥분된 목소리가 실험실을 가득 채웠다.",
                delay=0.05,
                pause=1.5
            ),
            StorySegment(
                "수십 년간의 연구와 준비가 이 순간을 위함이었다.",
                delay=0.05,
                pause=2.0
            ),
            StorySegment(
                "\n하지만 그 누구도 예상하지 못한 일이",
                delay=0.06,
                pause=1.5,
                color="yellow"
            ),
            StorySegment(
                "조용히 어둠 속에서 꿈틀거리고 있었다...",
                delay=0.06,
                pause=2.5,
                color="yellow"
            ),
            
            # 재앙의 시작
            StorySegment(
                "\n\"차원 게이트 개방... 3... 2... 1...\"",
                delay=0.1,
                pause=2.0,
                color="yellow"
            ),
            StorySegment(
                "\n하지만 첫 번째 차원 도약 실험에서...",
                delay=0.08,
                pause=2.0
            ),
            StorySegment(
                "아무도 예상하지 못한 일이 벌어졌다.",
                delay=0.08,
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "\n\"경고! 차원 공명 현상 발생!\"",
                delay=0.06,
                pause=1.5,
                color="red"
            ),
            StorySegment(
                "\"시공간 매트릭스가 불안정합니다!\"",
                delay=0.06,
                pause=1.5,
                color="red"
            ),
            StorySegment(
                "\"실험 중단! 즉시 실험을 중단하세요!\"",
                delay=0.06,
                pause=2.0,
                color="red"
            ),
            
            # 대재앙
            StorySegment(
                "\n시공간 교란 발생!",
                delay=0.2,
                pause=3.0,
                color="red"
            ),
            StorySegment(
                "\n하늘이 갈라지고, 대지가 진동했다.",
                delay=0.08,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "차원의 경계가 산산조각 나면서",
                delay=0.06,
                pause=1.5
            ),
            StorySegment(
                "과거, 현재, 미래의 모든 시대가 뒤섞이기 시작했다.",
                delay=0.06,
                pause=2.5
            ),
            StorySegment(
                "\n시간의 흐름이 왜곡되기 시작했다...",
                delay=0.08,
                pause=2.0,
                color="magenta"
            ),
            StorySegment(
                "어떤 곳에서는 시간이 거꾸로 흐르고,",
                delay=0.06,
                pause=1.8,
                color="magenta"
            ),
            StorySegment(
                "어떤 곳에서는 시간이 완전히 멈춰버렸다.",
                delay=0.06,
                pause=2.0,
                color="magenta"
            ),
            StorySegment(
                "\n공간의 법칙이 무너지면서",
                delay=0.08,
                pause=1.8,
                color="blue"
            ),
            StorySegment(
                "중력이 제멋대로 변하고,",
                delay=0.06,
                pause=1.5,
                color="blue"
            ),
            StorySegment(
                "거리의 개념 자체가 의미를 잃었다.",
                delay=0.06,
                pause=2.0,
                color="blue"
            ),
            StorySegment(
                "\n현실 자체가 일그러지면서",
                delay=0.08,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "물질과 에너지의 경계가 흐려졌다.",
                delay=0.06,
                pause=2.5,
                color="red"
            ),
            
            # 혼돈의 세계 - 간단한 마무리
            StorySegment(
                "\n그리고... 세상은 완전히 달라졌다.",
                delay=0.08,
                pause=3.0,
                color="white"
            ),
            StorySegment(
                "\n시공간의 혼돈 속에서",
                delay=0.06,
                pause=1.5
            ),
            StorySegment(
                "모든 것이 불가능해 보이는 일들이 현실이 되었다.",
                delay=0.06,
                pause=2.5
            ),
            StorySegment(
                "미래의 과학자가 돌도끼로 실험을 한다.",
                delay=0.05,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n모든 것이 뒤섞인 채로 새로운 질서를 찾기 시작한다.",
                delay=0.05,
                pause=1.8,
                color="yellow"
            ),
            StorySegment(
                "그리스의 철학자가 고장난 컴퓨터 앞에서 좌절하지만,",
                delay=0.05,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\nAI와 함께 새로운 진리를 탐구한다.",
                delay=0.05,
                pause=1.8,
                color="yellow"
            ),
            StorySegment(
                "해적이 우주선 조종법을 몰라 표류하지만,",
                delay=0.05,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n성간 항해의 새로운 길을 개척해낸다.",
                delay=0.05,
                pause=1.8,
                color="yellow"
            ),
            StorySegment(
                "기사가 레이저 검에 당황하면서도,",
                delay=0.05,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n과거의 기사도와 미래의 기술을 융합해낸다.",
                delay=0.05,
                pause=1.8,
                color="yellow"
            ),
            StorySegment(
                "\n모든 것이 혼란스럽지만,",
                delay=0.05,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "새로운 가능성들이 태어나고 있었다.",
                delay=0.05,
                pause=2.5,
                color="yellow"
            ),
            
            # 시공간 혼돈의 구체적 묘사
            StorySegment(
                "\n과거의 지혜와 미래의 기술이 만나고,",
                delay=0.06,
                pause=2.0,
                color="yellow"
            ),
            StorySegment(
                "서로 다른 시대의 법칙들이 충돌한다.",
                delay=0.06,
                pause=2.0,
                color="yellow"
            ),
            StorySegment(
                "\n하지만 그 혼돈 속에서도",
                delay=0.06,
                pause=2.0,
                color="blue"
            ),
            StorySegment(
                "새로운 가능성들이 태어나고 있었다.",
                delay=0.06,
                pause=2.0,
                color="blue"
            ),
            
            # 주인공의 등장
            StorySegment(
                "\n그리고 그 혼돈 속에서, 당신이 있다.",
                delay=0.08,
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "🌟 당신은 차원 항해사로서",
                delay=0.06,
                pause=1.5,
                color="cyan"
            ),
            StorySegment(
                "\n이 혼돈의 세계에서 길을 찾아야 한다.",
                delay=0.06,
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "과거의 기억이 미래의 예언이 된다.",
                delay=0.06,
                pause=2.5,
                color="magenta"
            ),
            StorySegment(
                "\n죽은 자가 살아서 걸어다니고,",
                delay=0.06,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "태어나지 않은 자가 이미 늙어간다.",
                delay=0.06,
                pause=3.0,
                color="white"
            ),
            
            # 주인공의 등장 - 더 극적으로
            StorySegment(
                "\n그리고... 이 모든 혼돈의 한복판에",
                delay=0.08,
                pause=2.5,
                color="cyan"
            ),
            StorySegment(
                "당신이 서 있다.",
                delay=0.08,
                pause=3.0,
                color="cyan"
            ),
            StorySegment(
                "\n당신은 차원 항해사...",
                delay=0.08,
                pause=2.0,
                color="yellow"
            ),
            StorySegment(
                "시공간을 넘나들 수 있는 유일한 존재.",
                delay=0.06,
                pause=2.5,
                color="yellow"
            ),
            StorySegment(
                "이 혼돈의 세계에서 질서를 찾을 수 있는",
                delay=0.06,
                pause=2.0,
                color="yellow"
            ),
            StorySegment(
                "마지막 희망.",
                delay=0.08,
                pause=3.0,
                color="yellow"
            ),
            
            # 사명감 부여
            StorySegment(
                "\n시공간 교란의 진정한 원인을 찾아야 한다.",
                delay=0.06,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "뒤섞인 시대들을 제자리로 돌려놓아야 한다.",
                delay=0.06,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "무너진 현실의 법칙을 다시 세워야 한다.",
                delay=0.06,
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "\n하지만 그 여정은 결코 쉽지 않을 것이다.",
                delay=0.06,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "혼자서는 절대 불가능한 일이다.",
                delay=0.06,
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "\n시공을 초월한 동료들을 만나야 한다.",
                delay=0.06,
                pause=2.0,
                color="green"
            ),
            StorySegment(
                "각기 다른 시대에서 온 영웅들과 함께",
                delay=0.06,
                pause=2.0,
                color="green"
            ),
            StorySegment(
                "이 불가능해 보이는 임무를 완수해야 한다.",
                delay=0.06,
                pause=3.0,
                color="green"
            ),
            
            # 모험의 시작
            StorySegment(
                "\n🌌 시공의 미로를 탐험하고",
                delay=0.05,
                pause=1.5,
                color="blue"
            ),
            StorySegment(
                "⚔️ 시대를 초월한 동료들과 함께",
                delay=0.05,
                pause=1.5,
                color="green"
            ),
            StorySegment(
                "🎭 운명의 실타래를 바로잡을 수 있을까?",
                delay=0.05,
                pause=3.0,
                color="yellow"
            ),
            StorySegment(
                "\n혹시 당신이 그 해답을 가지고 있는 건 아닐까?",
                delay=0.06,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "아니면... 당신 자신이 그 해답인 건 아닐까?",
                delay=0.08,
                pause=3.0,
                color="yellow"
            ),
            
            # 에필로그
            StorySegment(
                "\n✨ 모험이 시작된다... ✨",
                delay=0.1,
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "\n🌟 시공을 초월한 영웅들의 이야기",
                delay=0.08,
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "🌟 혼돈 속에서 피어나는 희망",
                delay=0.08,
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "🌟 그리고 당신의 전설이 시작된다",
                delay=0.08,
                pause=3.0,
                color="yellow"
            ),
            StorySegment(
                "\n[Enter 키를 눌러 운명을 받아들이세요]",
                delay=0.03,
                pause=0.5,
                color="green"
            )
        ]
    
    def get_chapter_intro(self, chapter: int) -> List[StorySegment]:
        """간단한 챕터 인트로 스토리"""
        intros = {
            1: [
                StorySegment(f"\n🌟 새로운 모험의 시작", color="yellow", delay=0.08, pause=2.0),
                StorySegment("\n깊은 차원 공간에서 이상한 빛이 새어나온다...", delay=0.05, pause=2.0),
                StorySegment("⚡ 시공간의 첫 번째 균열을 발견했다! ⚡", color="cyan", delay=0.06, pause=2.5)
            ],
            2: [
                StorySegment(f"\n🌟 과거로부터의 메아리", color="yellow", delay=0.08, pause=2.0),
                StorySegment("\n🏛️ 고대의 유적이 갑자기 나타났다...", delay=0.06, pause=2.0),
                StorySegment("\"...시간을 초월한 자여, 우리의 부름을 들어라...\"", color="magenta", delay=0.04, pause=2.5)
            ],
            3: [
                StorySegment(f"\n🌟 미래의 그림자", color="yellow", delay=0.08, pause=2.0),
                StorySegment("\n📡 갑자기 미래에서 온 통신이 포착된다...", delay=0.06, pause=2.0),
                StorySegment("\"...비상 신호... 시공간 붕괴 임계점 도달...\"", color="red", delay=0.04, pause=2.5)
            ]
        }
        return intros.get(chapter, [
            StorySegment(f"\n🌟 새로운 영역으로...", color="yellow", delay=0.08, pause=2.0),
            StorySegment("🚪 새로운 차원의 문이 열렸다...", delay=0.06, pause=2.0),
            StorySegment("당신의 모험은 계속된다...", color="cyan", delay=0.06, pause=3.0)
        ])
    
    def get_character_backstory(self, job_name: str) -> str:
        """확장된 직업별 배경 스토리 - 더욱 상세하고 흥미로운 버전 + 캐릭터 생성 맥락"""
        backstories = {
            "전사": "🗡️ 시공 교란이 일어난 그 순간, 고대 전장에서 싸우던 전설의 전사가 현대로 소환되었다. 수천 년의 전투 경험과 불굴의 의지를 가진 그는 이제 새로운 시대의 적들과 맞서야 한다. 당신이 그의 혼을 계승한 순간, 검을 쥐는 법을 본능적으로 알게 되었다.",
            
            "아크메이지": "🔮 차원 균열을 연구하던 천재 마법사. 시공간 교란의 순간 마법과 과학이 융합되는 기적을 목격했다. 이제 그는 고대 마법과 미래 기술을 모두 다루는 유일한 존재가 되었다. 그의 지식이 당신의 마음에 스며들어, 마법의 진리를 깨닫게 해준다.",
            
            "궁수": "🏹 시간의 흐름을 읽는 신비한 능력을 가진 명사수. 화살이 날아가는 궤적을 통해 미래를 예견하며, 적의 움직임을 미리 알아차린다. 시공 교란 속에서도 정확한 조준을 잃지 않는다. 당신이 활을 든 순간, 모든 목표가 명확하게 보이기 시작했다.",
            
            "도적": "🗡️ 차원 사이의 틈새를 자유자재로 넘나드는 그림자 요원. 시공간이 뒤섞인 혼돈 속에서 정보를 수집하고, 누구도 찾을 수 없는 비밀 통로를 개척한다. 그의 기술이 당신의 몸에 스며들어, 그림자처럼 움직이는 법을 터득했다.",
            
            "성기사": "🛡️ 신성한 빛의 힘으로 시공간의 어둠을 정화하는 기사. 차원 교란으로 생긴 어둠의 세력들과 맞서며, 혼돈 속에서 질서를 되찾으려 한다. 그의 검은 악을 베고 빛은 길을 밝힌다. 당신이 그의 신념을 받아들인 순간, 마음 속에 성스러운 빛이 타오르기 시작했다.",
            
            "암흑기사": "🌑 시공 교란의 어둠에 잠식되었지만, 아직 인간성을 잃지 않은 타락한 기사. 어둠의 힘을 다루면서도 정의를 추구하는 모순된 존재. 그의 내면에서는 빛과 어둠이 끊임없이 갈등한다. 당신이 그의 운명을 받아들인 순간, 어둠과 빛의 경계에서 균형을 찾는 법을 배웠다.",
            
            "몽크": "👊 내면의 평정심으로 시공간의 혼돈에 흔들리지 않는 수도승. 명상을 통해 시공간의 본질을 이해하며, 육체와 정신의 완벽한 조화로 차원의 힘을 다룬다. 그의 깨달음이 당신의 정신을 깨우쳐, 진정한 내면의 힘을 발견하게 해주었다.",
            
            "바드": "🎵 시대를 초월한 노래로 차원의 조화를 되찾으려는 음유시인. 그의 선율은 뒤섞인 시공간을 안정시키고, 고대의 지혜와 미래의 희망을 노래로 전한다. 당신이 그의 음성을 받아들인 순간, 세상의 모든 소리가 하나의 아름다운 선율로 들리기 시작했다.",
            
            "네크로맨서": "💀 죽음과 생명의 경계가 흐려진 세계에서 영혼을 다루는 술사. 시공 교란으로 인해 과거와 현재의 영혼들이 뒤섞이자, 그들의 목소리를 듣고 인도하는 역할을 맡게 되었다. 당신이 그의 능력을 계승한 순간, 죽음의 비밀과 생명의 진리를 동시에 깨달았다.",
            
            "용기사": "🐉 고대 용들과 계약을 맺고 시공간을 수호하는 용의 기사. 용의 힘과 지혜를 빌려 차원의 균형을 지키며, 하늘을 날며 세계 전체를 조망한다. 당신이 그의 계약을 이어받은 순간, 용의 숨결과 하늘의 자유를 느낄 수 있게 되었다.",
            
            "검성": "⚡ 검의 도를 통해 차원의 베일을 가르는 초월적 검사. 일검에 시공간을 자르고, 검기로 현실을 베어내는 경지에 도달했다. 그의 검은 불가능을 가능하게 만든다. 당신이 그의 검도를 전수받은 순간, 모든 것을 베어낼 수 있는 의지를 얻었다.",
            
            "정령술사": "🌟 자연의 정령들과 소통하여 세계의 균형을 지키는 술사. 시공 교란으로 혼란에 빠진 정령들을 달래며, 자연의 원시적 힘으로 세계를 치유하려 한다. 당신이 그의 능력을 받아들인 순간, 모든 자연의 목소리를 들을 수 있게 되었다.",
            
            "시간술사": "⏰ 시공 교란의 원인을 찾아 시간 자체를 조작하는 마법사. 과거로 돌아가 실수를 바로잡고, 미래를 내다보며 최선의 선택을 찾는다. 시간은 그에게 있어 도구일 뿐이다. 당신이 그의 지식을 받아들인 순간, 시간의 흐름을 감지하고 조작하는 법을 배웠다.",
            
            "연금술사": "⚗️ 과학과 마법의 융합으로 새로운 가능성을 탐구하는 연구자. 시공 교란으로 뒤섞인 다양한 시대의 지식을 조합하여 기적 같은 물질들을 만들어낸다. 당신이 그의 연구를 이어받은 순간, 모든 물질의 본질을 꿰뚫어보는 눈을 얻었다.",
            
            "차원술사": "🌌 차원 항해 기술의 전문가로 교란된 공간을 수정하려는 학자. 시공간 교란의 원인을 가장 잘 이해하며, 차원의 문을 열고 닫는 능력을 가지고 있다. 당신이 그의 이론을 받아들인 순간, 공간의 구조를 이해하고 조작하는 능력을 얻었다.",
            
            "마검사": "🗡️ 마법과 검술을 완벽히 융합한 시공간의 수호자. 검에 마법을 깃들여 공간을 베고 시간을 자르며, 검과 마법이 하나가 된 완전한 전투 스타일을 구사한다. 당신이 그의 기예를 이어받은 순간, 검과 마법의 완벽한 조화를 체득했다.",
            
            "기계공학자": "🔧 미래 기술과 고대 마법을 결합한 하이브리드 엔지니어. 마법으로 작동하는 기계들을 만들어내며, 시공 교란으로 뒤섞인 기술들을 융합하여 새로운 발명품을 창조한다. 당신이 그의 지식을 받아들인 순간, 기계와 마법이 만나는 접점을 이해하게 되었다.",
            
            "무당": "🔯 영계와 현실계의 경계를 넘나들며 영혼들을 인도하는 무녀. 시공 교란으로 길을 잃은 영혼들을 위로하고, 신령들의 힘을 빌려 세계의 조화를 되찾으려 한다. 당신이 그의 능력을 계승한 순간, 보이지 않는 세계의 존재들과 소통할 수 있게 되었다.",
            
            "암살자": "🔪 그림자 속에서 시공간의 적들을 제거하는 은밀한 처치자. 차원의 틈새를 이용해 순간이동하며, 아무도 모르게 나타나 임무를 완수하고 사라진다. 당신이 그의 기술을 받아들인 순간, 어둠 속에서 움직이는 법과 적을 무력화하는 비법을 터득했다.",
            
            "해적": "🏴‍☠️ 차원간 바다를 항해하며 보물을 찾는 모험가. 시공간의 파도를 타고 다양한 차원을 모험하며, 전설의 보물들을 찾아 무한한 바다를 항해한다. 당신이 그의 모험 정신을 받아들인 순간, 자유로운 영혼과 보물을 찾는 직감을 얻었다.",
            
            "사무라이": "🗾 명예와 의리로 혼돈의 시대를 살아가는 전통 무사. 무사도 정신으로 시공간의 혼돈에 맞서며, 한 번의 베기로 모든 것을 결정짓는 일격필살의 달인이다. 당신이 그의 정신을 받아들인 순간, 명예로운 길을 걷는 의지와 완벽한 한 검의 힘을 얻었다.",
            
            "드루이드": "🌿 자연의 힘으로 교란된 세계의 치유를 꿈꾸는 수호자. 동물들과 대화하고 식물들을 조종하며, 자연의 생명력으로 시공간의 상처를 치유하려 한다. 당신이 그의 능력을 받아들인 순간, 모든 생명체와 교감하고 자연의 힘을 빌리는 법을 배웠다.",
            
            "철학자": "🧠 시공 교란의 원리를 이론적으로 해명하려는 현자. 모든 현상을 논리로 분석하고, 사고의 힘만으로 현실을 바꿀 수 있는 깨달음에 도달했다. 당신이 그의 지혜를 받아들인 순간, 세상의 진리를 꿰뚫어보는 통찰력과 논리적 사고력을 얻었다.",
            
            "검투사": "🏛️ 차원간 투기장에서 살아남은 불굴의 투사. 수많은 차원의 강자들과 싸워 이기며 단련된 육체와 정신으로, 어떤 적과도 정면승부를 두려워하지 않는다. 당신이 그의 의지를 받아들인 순간, 불굴의 투지와 어떤 상황에서도 굴복하지 않는 정신력을 얻었다.",
            
            "기사": "🐎 정의와 명예를 위해 혼돈의 세계에 질서를 가져오려는 기사. 기사도 정신으로 약자를 보호하고 악을 물리치며, 혼란한 세상에 희망의 빛이 되고자 한다. 당신이 그의 이상을 받아들인 순간, 정의로운 마음과 약자를 보호하려는 강한 의지를 얻었다.",
            
            "신관": "✨ 신들의 뜻에 따라 세계의 정화를 담당하는 성직자. 신성한 기도와 축복으로 어둠을 물리치고, 신의 은총을 받아 기적을 일으킨다. 당신이 그의 신앙을 받아들인 순간, 신성한 힘과 치유의 기적을 행하는 능력을 얻었다.",
            
            "광전사": "💥 시공 교란의 영향으로 광기를 얻었지만 그 힘으로 싸우는 전사. 광기와 이성 사이에서 줄타기하며, 광폭한 힘으로 적들을 압도한다. 당신이 그의 광기를 받아들인 순간, 극한 상황에서 폭발하는 잠재력과 절대 포기하지 않는 집념을 얻었다."
        }
        return backstories.get(job_name, "🌟 시공간의 혼돈 속에서 자신만의 길을 찾아가는 신비로운 모험가. 과거도 미래도 아닌, 오직 현재를 살아가며 운명을 개척해나가는 자. 당신이 그의 정신을 받아들인 순간, 무한한 가능성과 독창적인 힘을 얻었다.")
    
    def get_trait_backstory(self, trait_name: str) -> str:
        """특성별 배경 스토리"""
        trait_stories = {
            "동물 변신": "🐺 고대 드루이드의 변신술이 당신의 혈관에 흐른다. 늑대의 야성, 곰의 힘, 독수리의 자유... 자연의 모든 형태를 체험할 수 있는 축복받은 능력이다.",
            
            "원소 친화": "🌪️ 시공간 교란으로 인해 원소들이 당신에게 친밀감을 느낀다. 불, 물, 바람, 대지... 모든 원소가 당신의 의지에 기꺼이 응답한다.",
            
            "전투 광": "⚔️ 전장의 광기가 당신의 본능을 깨운다. 절망적인 상황일수록 더욱 강해지는 전사의 혼이 당신 안에 잠들어 있다.",
            
            "치유술사": "✨ 생명의 근원적 힘이 당신의 손끝에서 흘러나온다. 상처를 치유하고 고통을 덜어주는 것이 당신의 천명이다.",
            
            "시간 감각": "⏰ 시공간 교란의 영향으로 시간의 흐름을 직감적으로 파악할 수 있게 되었다. 위험한 순간을 미리 감지하는 예지력을 가지고 있다.",
            
            "마법 저항": "🛡️ 마법적 공격에 대한 천연 저항력을 가지고 있다. 시공간 교란의 마법적 에너지가 당신을 더욱 강하게 만들었다.",
            
            "상인의 눈": "💰 가치 있는 것을 알아보는 타고난 직감을 가지고 있다. 숨겨진 보물과 거래의 기회를 놓치지 않는다.",
            
            "학자의 지혜": "📚 지식에 대한 갈망과 학습 능력이 뛰어나다. 새로운 것을 배우고 이해하는 속도가 남들보다 빠르다.",
            
            "운명의 가호": "🍀 운명의 여신이 당신을 특별히 돌보고 있다. 절체절명의 순간에 기적적인 행운이 찾아온다.",
            
            "영혼 시야": "👁️ 영혼의 세계를 볼 수 있는 신비한 능력을 가지고 있다. 숨겨진 진실과 영혼의 상태를 파악할 수 있다."
        }
        return trait_stories.get(trait_name, "✨ 시공간의 혼돈 속에서 당신만의 특별한 재능이 각성했다. 이 능력이 어떤 운명을 가져다줄지는 당신의 선택에 달려있다.")
    
    def get_difficulty_selection_story(self, difficulty: str) -> List[StorySegment]:
        """난이도 선택 시 스토리"""
        stories = {
            "평온": [
                StorySegment("\n🌸 평화로운 길을 선택했다.", delay=0.06, pause=1.5, color="green"),
                StorySegment("🕊️ 시공간의 혼돈도 당신 앞에서는 조용해진다.", delay=0.05, pause=2.0, color="white"),
                StorySegment("✨ 여유로운 마음으로 모험을 즐길 수 있을 것이다.", delay=0.05, pause=2.5, color="cyan")
            ],
            "보통": [
                StorySegment("\n⚖️ 균형 잡힌 길을 선택했다.", delay=0.06, pause=1.5, color="blue"),
                StorySegment("🌟 적당한 도전과 성취감을 느낄 수 있을 것이다.", delay=0.05, pause=2.0, color="white"),
                StorySegment("💫 모험가로서 성장하기에 완벽한 조건이다.", delay=0.05, pause=2.5, color="cyan")
            ],
            "도전": [
                StorySegment("\n🔥 험난한 길을 선택했다.", delay=0.06, pause=1.5, color="yellow"),
                StorySegment("⚔️ 더 큰 위험이 더 큰 보상을 가져다줄 것이다.", delay=0.05, pause=2.0, color="white"),
                StorySegment("💪 진정한 영웅이 되기 위한 시련이 기다린다.", delay=0.05, pause=2.5, color="red")
            ],
            "악몽": [
                StorySegment("\n💀 악몽의 길을 선택했다.", delay=0.06, pause=1.5, color="red"),
                StorySegment("🌪️ 시공간의 혼돈이 당신을 시험할 것이다.", delay=0.05, pause=2.0, color="magenta"),
                StorySegment("⚡ 오직 최고의 영웅만이 살아남을 수 있다.", delay=0.05, pause=2.5, color="yellow")
            ],
            "지옥": [
                StorySegment("\n🔥 지옥의 길을 선택했다.", delay=0.08, pause=2.0, color="red"),
                StorySegment("💥 모든 것이 당신의 적이 될 것이다.", delay=0.06, pause=2.0, color="red"),
                StorySegment("👑 하지만 그것을 극복한다면... 전설이 될 것이다.", delay=0.05, pause=3.0, color="yellow")
            ]
        }
        return stories.get(difficulty, [
            StorySegment(f"\n🎯 {difficulty} 난이도를 선택했다.", delay=0.06, pause=1.5, color="white"),
            StorySegment("🌟 당신의 모험이 시작된다.", delay=0.05, pause=2.5, color="cyan")
        ])
    
    def get_sephiroth_encounter_story(self) -> List[StorySegment]:
        """30층에서 세피로스와 첫 조우 시 나오는 극도로 무서운 스토리"""
        return [
            # 불길한 시작
            StorySegment(
                "지하 30층...",
                delay=0.2,
                pause=3.0,
                color="white"
            ),
            StorySegment(
                "공기가 차갑다.",
                delay=0.15,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "너무나도 조용하다.",
                delay=0.15,
                pause=3.0,
                color="white"
            ),
            
            # 시체들의 발견
            StorySegment(
                "\n바닥에 뭔가가 있다...",
                delay=0.12,
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "시체다.",
                delay=0.2,
                pause=3.0,
                color="white"
            ),
            StorySegment(
                "수십 구의 시체가 벽을 따라 늘어서 있다.",
                delay=0.08,
                pause=3.0,
                color="white"
            ),
            StorySegment(
                "모두 웃고 있다.",
                delay=0.2,
                pause=4.0,
                color="red"
            ),
            
            # 실험실의 참상
            StorySegment(
                "\n실험실은 지옥이었다.",
                delay=0.12,
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "실험대 위에는 아직도 뜨거운 기계 부품들이 놓여있고,",
                delay=0.08,
                pause=3.0,
                color="red"
            ),
            StorySegment(
                "벽에는 수많은 차원 파편들의 잔해가 진열되어 있다.",
                delay=0.08,
                pause=4.0,
                color="red"
            ),
            StorySegment(
                "천장에는 무언가가 거꾸로 매달려 있다.",
                delay=0.08,
                pause=4.0,
                color="red"
            ),
            StorySegment(
                "모든 차원 실험들이 끔찍한 왜곡 속에서 실패했고...",
                delay=0.1,
                pause=3.0,
                color="red"
            ),
            StorySegment(
                "아직도 에너지가 새어나오고 있다.",
                delay=0.12,
                pause=5.0,
                color="red"
            ),
            
            # 세피로스의 등장
            StorySegment(
                "\n\"누군가 왔구나...\"",
                delay=0.15,
                pause=3.0,
                color="magenta"
            ),
            StorySegment(
                "뒤에서 목소리가 들린다.",
                delay=0.12,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "천천히 돌아보니...",
                delay=0.15,
                pause=3.0,
                color="white"
            ),
            
            # 세피로스의 모습
            StorySegment(
                "\n그곳에는 한 남자가 서 있었다.",
                delay=0.12,
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "흰 가운을 입고 있지만,",
                delay=0.1,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "가운은 피로 완전히 물들어 있었다.",
                delay=0.08,
                pause=3.0,
                color="red"
            ),
            StorySegment(
                "그의 손에는 아직도 적혈구가 뚝뚝 떨어지고 있고,",
                delay=0.08,
                pause=3.5,
                color="red"
            ),
            StorySegment(
                "입가에는 기괴한 미소가 걸려있다.",
                delay=0.08,
                pause=3.0,
                color="red"
            ),
            
            # 세피로스의 대사 - 광기
            StorySegment(
                "\n\"내 이름은 세피로스.\"",
                delay=0.12,
                pause=2.5,
                color="magenta"
            ),
            StorySegment(
                "\"이곳의... 예술가라고 할 수 있지.\"",
                delay=0.1,
                pause=3.0,
                color="magenta"
            ),
            StorySegment(
                "\"보다시피, 나는 생명체들로 작품을 만드는 것을 좋아한다.\"",
                delay=0.08,
                pause=4.0,
                color="magenta"
            ),
            StorySegment(
                "\"특히... 산 채로 말이지. 크크크...\"",
                delay=0.1,
                pause=4.0,
                color="red"
            ),
            
            # 실험에 대한 설명
            StorySegment(
                "\n\"차원 항해 기술? 그건 표면일 뿐이야.\"",
                delay=0.08,
                pause=3.0,
                color="magenta"
            ),
            StorySegment(
                "\"진짜 목적은... 영혼을 가두는 거였어.\"",
                delay=0.08,
                pause=3.5,
                color="magenta"
            ),
            StorySegment(
                "\"이 실험실에 있는 시체들... 모두 내 작품이지.\"",
                delay=0.08,
                pause=4.0,
                color="red"
            ),
            StorySegment(
                "\"그들은 죽었지만, 영혼은 아직도 여기 갇혀있어.\"",
                delay=0.08,
                pause=4.0,
                color="red"
            ),
            StorySegment(
                "\"영원히 고통받으면서 말이야! 하하하하!\"",
                delay=0.08,
                pause=4.0,
                color="red"
            ),
            
            # 더 잔혹한 진실
            StorySegment(
                "\n\"저 벽에 걸린 실험체들... 모두 살아있을 때 실험했지.\"",
                delay=0.08,
                pause=4.0,
                color="red"
            ),
            StorySegment(
                "\"그들의 비명소리가 얼마나 아름다웠는지...\"",
                delay=0.08,
                pause=3.5,
                color="red"
            ),
            StorySegment(
                "\"천장의 실험체들은 각종 독을 주입하며 실험했어.\"",
                delay=0.08,
                pause=4.0,
                color="red"
            ),
            StorySegment(
                "\"고통과 절망이 동시에 터지는 순간... 정말 예술적이었지!\"",
                delay=0.08,
                pause=5.0,
                color="red"
            ),
            
            # 주인공에 대한 관심
            StorySegment(
                "\n\"그런데 너는... 흥미롭구나.\"",
                delay=0.12,
                pause=3.0,
                color="magenta"
            ),
            StorySegment(
                "\"여기까지 내려온 첫 번째 '생존자'야.\"",
                delay=0.1,
                pause=3.0,
                color="magenta"
            ),
            StorySegment(
                "\"너도 내 컬렉션에 추가해주마.\"",
                delay=0.1,
                pause=3.0,
                color="red"
            ),
            StorySegment(
                "\"하지만 그 전에... 좀 더 재미있게 놀아보자.\"",
                delay=0.08,
                pause=3.5,
                color="red"
            ),
            
            # 협박과 예고
            StorySegment(
                "\n\"나는 너의 공포를 맛보고 싶어.\"",
                delay=0.1,
                pause=3.0,
                color="red"
            ),
            StorySegment(
                "\"절망에 빠진 너의 표정을 보고 싶고...\"",
                delay=0.08,
                pause=3.0,
                color="red"
            ),
            StorySegment(
                "\"마지막에 도움을 청하며 울부짖는 소리를 듣고 싶어.\"",
                delay=0.08,
                pause=4.0,
                color="red"
            ),
            StorySegment(
                "\"그리고 마지막에는... 너를 영원히 여기 가둬두겠어.\"",
                delay=0.08,
                pause=4.0,
                color="red"
            ),
            
            # 광기의 절정
            StorySegment(
                "\n\"지금까지의 모든 모험이 무의미했다는 걸 깨달을 때...\"",
                delay=0.08,
                pause=4.0,
                color="red"
            ),
            StorySegment(
                "\"그 순간의 절망이 얼마나 달콤할까! 하하하하하!\"",
                delay=0.08,
                pause=4.0,
                color="red"
            ),
            StorySegment(
                "\"자, 이제 시작해보자. 나의 마지막 실험을!\"",
                delay=0.1,
                pause=5.0,
                color="red"
            ),
            
            # 전투 직전 경고
            StorySegment(
                "\n█▓▒░ WARNING: BOSS ENCOUNTER ░▒▓█",
                delay=0.15,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "●○◆ 세피로스가 당신을 노려보고 있습니다 ◆○●",
                delay=0.08,
                pause=3.0,
                color="red"
            ),
            StorySegment(
                "■□▓ 도망칠 수 없습니다... ▓□■",
                delay=0.1,
                pause=5.0,
                color="red"
            )
        ]
        
    def get_true_ending_story(self) -> List[StorySegment]:
        """세피로스 처치 후 진 엔딩 스토리"""
        return [
            StorySegment(
                "\n세피로스가 쓰러졌다...",
                delay=0.08,
                pause=3.0,
                color="white"
            ),
            StorySegment(
                "그의 마지막 말이 실험실에 울려 퍼진다.",
                delay=0.06,
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "\n\"이것으로... 끝이 아니다...\"",
                delay=0.08,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\"진실은... 이미 퍼졌다...\"",
                delay=0.08,
                pause=3.0,
                color="red"
            ),
            StorySegment(
                "\n// SYSTEM RESTORATION IN PROGRESS //",
                delay=0.1,
                pause=2.0,
                color="green"
            ),
            StorySegment(
                "// MEMORY BANKS CLEARED //",
                delay=0.08,
                pause=1.5,
                color="green"
            ),
            StorySegment(
                "// CORRUPTION REMOVED //",
                delay=0.08,
                pause=2.0,
                color="green"
            ),
            StorySegment(
                "\n갑자기 모든 것이 명확해진다.",
                delay=0.06,
                pause=2.5,
                color="cyan"
            ),
            StorySegment(
                "시공간의 혼돈이 점차 안정되기 시작한다.",
                delay=0.06,
                pause=2.5,
                color="cyan"
            ),
            StorySegment(
                "\n세피로스의 실험실에서 발견한 진실...",
                delay=0.06,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "차원 실험의 실패는 그의 의도적인 조작이었다.",
                delay=0.05,
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "인류를 강제 진화시키려는 광기어린 계획.",
                delay=0.05,
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "\n하지만 이제 모든 것이 끝났다.",
                delay=0.06,
                pause=2.0,
                color="green"
            ),
            StorySegment(
                "시공간이 정상으로 돌아가고 있다.",
                delay=0.05,
                pause=2.5,
                color="green"
            ),
            StorySegment(
                "\n당신은 진정한 영웅이 되었다.",
                delay=0.08,
                pause=2.0,
                color="yellow"
            ),
            StorySegment(
                "차원의 혼돈을 멈추고,",
                delay=0.06,
                pause=2.0,
                color="yellow"
            ),
            StorySegment(
                "세계를 구원한 진정한 차원 항해사.",
                delay=0.06,
                pause=3.0,
                color="yellow"
            ),
            StorySegment(
                "\n🌟 TRUE ENDING UNLOCKED 🌟",
                delay=0.1,
                pause=2.0,
                color="gold"
            ),
            StorySegment(
                "「Dawn of Stellar - Complete」",
                delay=0.08,
                pause=3.0,
                color="gold"
            ),
            # 진실 복구 - 원래 크레딧
            StorySegment(
                "\n// REALITY RESTORATION COMPLETE //",
                delay=0.1,
                pause=2.0,
                color="green"
            ),
            StorySegment(
                "// ACCESSING TRUE MEMORY BANKS //",
                delay=0.08,
                pause=2.0,
                color="green"
            ),
            StorySegment(
                "\n실제 제작자 정보가 복구되었습니다...",
                delay=0.06,
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "\n      --  🌟 D A W N   O F   S T E L L A R 🌟  --",
                delay=0.05,
                pause=2.0,
                color="yellow"
            ),
            StorySegment(
                "                        TRULY DIRECTED BY.. APTOL",
                delay=0.05,
                pause=3.0,
                color="cyan"
            ),
            StorySegment(
                "                    💎 THE REAL MASTERMIND 💎",
                delay=0.04,
                pause=2.0,
                color="gold"
            ),
            StorySegment(
                "                  🎮 GAME DEVELOPER EXTRAORDINAIRE 🎮",
                delay=0.04,
                pause=5.0,
                color="gold"
            )
        ]
    
    def display_story_with_typing_effect(self, segments: List[StorySegment]):
        """타이핑 효과 + Enter 전체 스킵 (콘솔/파이프 모두)
        반환값: True이면 중간 스킵 발생(또는 키보드 인터럽트), False이면 정상 종료
        """
        import sys, time, os
        
        # 글리치 모드에서 추가 화면 클리어
        if self.is_glitch_mode():
            try:
                windows = sys.platform == 'win32'
                pipe_mode = windows and (not sys.stdin.isatty()) and os.getenv('SUBPROCESS_MODE') == '1'
                
                if not pipe_mode:
                    print("\033[2J\033[H")  # 화면 클리어
                    print("\033[3J")        # 스크롤백 버퍼도 클리어
                    for _ in range(3):      # 글리치 모드에서 더 많은 빈 줄
                        print()
                else:
                    for _ in range(3):
                        sys.stdout.write("\r\n")
                    sys.stdout.flush()
            except:
                pass
        
        # 스토리 재생 시작 플래그
        self.running_story = True
        # 파이프 모드라면 이제서야 watcher 시작 (일반 입력 훔치지 않도록)
        if os.getenv('SUBPROCESS_MODE') == '1':
            self._start_stdin_watcher()
        try:
            for segment in segments:
                # 불필요한 시작 줄바꿈 정리: 텍스트가 '\n'으로 시작하면 한 번만 제거
                if segment.text.startswith('\n'):
                    # 여러 개의 선행 줄바꿈은 하나로 압축 (완전 제거하지 않음)
                    original = segment.text
                    # 첫 연속 \n 길이 계산
                    i = 0
                    while i < len(original) and original[i] == '\n':
                        i += 1
                    # 하나만 남기고 나머지는 제거
                    compressed = '\n' + original[i:]
                    if compressed != original:
                        segment = StorySegment(compressed, delay=segment.delay, pause=segment.pause, color=segment.color)
                
                # 글리치 모드에서 무서운 효과음 재생
                if self.is_glitch_mode():
                    import random
                    # 빨간색 글리치 텍스트일 때 특별한 효과음 (100% 확률)
                    if segment.color == "red" and any(glitch in segment.text for glitch in ["█▓▒", "■□▓", "●○◆", "▓▒░"]):
                        self._play_random_glitch_sfx()
                    # 세피로스 관련 텍스트일 때
                    elif "세피로스" in segment.text or "SEPHIROTH" in segment.text:
                        self._play_sephiroth_sfx()
                    # 컴퓨터실/연구소 느낌: 모든 텍스트에서 높은 확률로 비프음 (70% 확률)
                    elif random.random() < 0.7:
                        self._play_random_glitch_sfx()
                    
                    # 추가 랜덤 비프음: 긴 텍스트의 경우 중간에도 비프음 (50% 확률)
                    if len(segment.text) > 50 and random.random() < 0.5:
                        import time
                        # 텍스트 중간에 비프음을 위한 지연 타이머
                        self._schedule_mid_text_beep = time.time() + random.uniform(1.0, 3.0)
                
                if self._skip_requested:
                    # 세피로스 개입 시도
                    if self._sephiroth_interrupt_skip():
                        # 개입 성공 시 스킵 취소하고 계속 진행
                        self._skip_requested = False
                        continue
                    else:
                        # 개입 실패 시 정상 스킵
                        print("\n[스토리를 건너뜁니다...]")
                        return True
                windows = sys.platform == 'win32'
                pipe_mode = windows and (not sys.stdin.isatty()) and os.getenv('SUBPROCESS_MODE') == '1'
                if windows and not pipe_mode:
                    import msvcrt
                    codes = self._get_color_codes()
                    print(codes.get(segment.color, ''), end='')
                    
                    # 🎯 글리치 모드에서 텍스트에 글리치 효과 적용
                    display_text = segment.text
                    actual_delay = segment.delay
                    if self.is_glitch_mode():
                        display_text = self.get_glitch_text(segment.text)
                        # 글리치 모드에서는 타이핑 속도를 20% 느리게
                        actual_delay = segment.delay * 1.2
                    
                    # 🎵 세피로스 감지 시 긴 비프음
                    if self.is_glitch_mode() and ('세피로스' in display_text or 'Sephiroth' in display_text or 'SEPHIROTH' in display_text):
                        self._play_sephiroth_long_beep()
                    
                    for ch in display_text:
                        # 🔊 글리치 모드에서 타이핑 중 랜덤 비프음 (컴퓨터실 느낌)
                        if self.is_glitch_mode():
                            import random, time
                            # 5% 확률로 각 문자마다 비프음 (매우 자주)
                            if random.random() < 0.05:
                                self._play_random_glitch_sfx()
                            # 스케줄된 중간 비프음 체크
                            if hasattr(self, '_schedule_mid_text_beep') and time.time() >= self._schedule_mid_text_beep:
                                self._play_random_glitch_sfx()
                                delattr(self, '_schedule_mid_text_beep')
                        
                        if self._skip_requested:
                            # 세피로스 개입 시도
                            if self._sephiroth_interrupt_skip():
                                self._skip_requested = False
                                continue
                            else:
                                print(codes['reset'])
                                print("\n[스토리를 건너뜁니다...]")
                                return True
                        if msvcrt.kbhit():
                            b = msvcrt.getch()
                            if b in (b'\r', b'\n'):
                                print(codes['reset'])
                                print("\n[스토리를 건너뜁니다...]")
                                return
                        print(ch, end='', flush=True)
                        time.sleep(actual_delay)  # 조정된 딜레이 사용
                    print(codes['reset'], end='')
                    if not (segment.text.startswith('══') or segment.text.strip().startswith('🌟')):
                        print()
                    end_time = time.time() + segment.pause
                    while time.time() < end_time:
                        if self._skip_requested:
                            print("\n[스토리를 건너뜁니다...]")
                            return True
                        if msvcrt.kbhit() and msvcrt.getch() in (b'\r', b'\n'):
                            print("\n[스토리를 건너뜁니다...]")
                            return True
                        time.sleep(0.01)
                else:
                    # 파이프 / Unix 경로: _skip_requested 플래그만 감시
                    self._type_text_with_skip(segment.text, segment.delay, segment.color)
                    end_time = time.time() + segment.pause
                    while time.time() < end_time:
                        if self._skip_requested:
                            print("\n[스토리를 건너뜁니다...]")
                            return
                        time.sleep(0.01)
        except KeyboardInterrupt:
            print("\n[스토리를 건너뜁니다...]")
            return True
        finally:
            self.running_story = False
            self._skip_requested = False
            # 스토리 종료되면 watcher 자연 종료 대기 (플래그 false로 루프 탈출)
        return False
    
    def _check_enter_key(self):
        """Enter 키 입력 확인 (크로스 플랫폼)"""
        if self.keyboard_input:
            try:
                # non-blocking 방식으로 키 입력 확인
                # subprocess 환경에서는 이 방법이 더 안정적
                import os
                if os.getenv('SUBPROCESS_MODE') == '1':
                    # subprocess 환경에서는 즉시 return
                    return False
                
                # Windows에서 msvcrt.kbhit() 사용
                import os
                if os.name == 'nt':
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        if key == b'\r' or key == b'\n':  # Enter 키
                            return True
                        # 다른 키는 버퍼에서 제거
                        return False
                else:
                    # Unix 계열에서는 select 사용
                    import select
                    import sys
                    if select.select([sys.stdin], [], [], 0.0)[0]:
                        key = sys.stdin.read(1)
                        if key == '\n':
                            return True
                return False
            except:
                return False
        else:
            # 백업 방법: select 사용 (Linux/Mac)
            try:
                import select
                import sys
                if select.select([sys.stdin], [], [], 0.0)[0]:
                    key = sys.stdin.read(1)
                    if key == '\n':
                        return True
                return False
            except:
                return False
    
    def _type_text_with_skip(self, text: str, delay: float, color: str = "white"):
        """타이핑 효과 with 스킵 기능
        - Windows 파이프 모드: select() 미사용 (WinError 10038 회피)
        - Unix: select()로 Enter 감시
        """
        import sys, time
        windows = sys.platform == 'win32'
        pipe_mode = windows and (not sys.stdin.isatty()) and os.getenv('SUBPROCESS_MODE') == '1'

        # 🎯 글리치 모드에서 텍스트에 글리치 효과 적용
        display_text = text
        actual_delay = delay
        if self.is_glitch_mode():
            display_text = self.get_glitch_text(text)
            # 글리치 모드에서는 타이핑 속도를 20% 느리게
            actual_delay = delay * 1.2

        # 모바일/서브프로세스 모드에서는 과도한 선행 줄바꿈을 1개로 축약
        if pipe_mode and display_text.startswith('\n'):
            import re
            display_text = re.sub(r'^(\n)+', '\n', display_text)
        color_codes = self._get_color_codes()
        print(color_codes.get(color, ''), end='')

        if windows:
            # 콘솔(tty) 아닌 파이프에서는 watcher 플래그(_skip_requested)만 사용
            for ch in display_text:
                # 🔊 글리치 모드에서 타이핑 중 랜덤 비프음 (Windows 파이프)
                if self.is_glitch_mode():
                    import random
                    if random.random() < 0.05:  # 5% 확률
                        self._play_random_glitch_sfx()
                
                if self._skip_requested:
                    print(color_codes['reset'])
                    return True
                print(ch, end='', flush=True)
                time.sleep(actual_delay)  # 조정된 딜레이 사용
        else:
            # Unix 계열: non-blocking select 사용
            try:
                import select
                for ch in display_text:
                    # 🔊 글리치 모드에서 타이핑 중 랜덤 비프음 (Unix)
                    if self.is_glitch_mode():
                        import random
                        if random.random() < 0.05:  # 5% 확률
                            self._play_random_glitch_sfx()
                    if self._skip_requested:
                        print(color_codes['reset'])
                        return True
                    if select.select([sys.stdin], [], [], 0.0)[0]:
                        key = sys.stdin.read(1)
                        if key == '\n':
                            print(color_codes['reset'])
                            return True
                    print(ch, end='', flush=True)
                    time.sleep(actual_delay)  # 조정된 딜레이 사용
            except Exception:
                # 실패 시 단순 출력
                for ch in display_text:
                    # 🔊 글리치 모드에서 타이핑 중 랜덤 비프음 (Unix 폴백)
                    if self.is_glitch_mode():
                        import random
                        if random.random() < 0.05:  # 5% 확률
                            self._play_random_glitch_sfx()
                    
                    if self._skip_requested:
                        print(color_codes['reset'])
                        return True
                    print(ch, end='', flush=True)
                    time.sleep(actual_delay)  # 조정된 딜레이 사용

        # 색상 리셋 후 세그먼트마다 항상 한 줄만 개행 (플랫폼별로 정확히 1회)
        print(color_codes['reset'], end='')
        if os.name == 'nt':
            sys.stdout.write("\r\n")
        else:
            print()
        sys.stdout.flush()
        return False
    
    def _get_color_codes(self):
        """컬러 코드 반환"""
        return {
            "white": "\033[97m",
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "magenta": "\033[95m",
            "cyan": "\033[96m",
            "gold": "\033[93m\033[1m",  # 밝은 노란색 + 굵게
            "reset": "\033[0m"
        }
    
    def _type_text(self, text: str, delay: float, color: str = "white"):
        """타이핑 효과 (기본, 스킵 기능 없음)"""
        color_codes = self._get_color_codes()
        
        print(color_codes.get(color, ""), end="")
        for char in text:
            print(char, end="", flush=True)
            time.sleep(delay)
        print(color_codes["reset"], end="")
        print()  # 줄바꿈

    def _flush_input_buffer(self):
        """입력 버퍼 플러시 (오프닝 시작 직전 잔여 입력 제거)
        - Windows 콘솔: msvcrt로 안전하게 비우기
        - Unix: select로 논블로킹 읽기
        - 파이프/서브프로세스 모드에서는 입력을 건드리지 않음
        """
        try:
            import os, sys
            # 서브프로세스/파이프 모드에서는 건드리지 않음 (입력 공유 이슈 회피)
            if os.getenv('SUBPROCESS_MODE') == '1':
                return
            if os.name == 'nt':
                import msvcrt
                # 가능한 모든 키를 즉시 소모
                while msvcrt.kbhit():
                    try:
                        msvcrt.getch()
                    except Exception:
                        break
            else:
                import select
                # 입력이 없을 때까지 1바이트씩 소모
                while True:
                    r, _, _ = select.select([sys.stdin], [], [], 0)
                    if not r:
                        break
                    try:
                        sys.stdin.read(1)
                    except Exception:
                        break
        except Exception:
            # 실패해도 게임 진행에 영향 주지 않음
            pass
    
    def show_opening_story(self):
        """오프닝 스토리 표시"""
        if self.story_seen:
            return
        
        # 화면 초기화: 글리치 모드든 일반 모드든 동일하게 빈 공간에서 시작
        try:
            windows = sys.platform == 'win32'
            pipe_mode = windows and (not sys.stdin.isatty()) and os.getenv('SUBPROCESS_MODE') == '1'
        except Exception:
            pipe_mode = False
        
        # 강력한 화면 클리어 (글리치 모드에서도 확실하게)
        if not pipe_mode:
            print("\033[2J\033[H")  # 화면 클리어
            print("\033[3J")        # 스크롤백 버퍼도 클리어
            for _ in range(5):      # 여러 줄 개행으로 확실히 분리
                print()
        else:
            # 파이프에서는 여러 CRLF 출력
            for _ in range(5):
                sys.stdout.write("\r\n")
            sys.stdout.flush()
        
        # 글리치 모드에 따른 BGM과 효과음 재생
        if self.is_glitch_mode():
            # 글리치 모드: 추가 화면 클리어와 함께
            if not pipe_mode:
                print("\033[2J\033[H")  # 글리치 모드에서 한 번 더 클리어
                print()
            
            # 강력한 BGM 정지 메시지와 실행
            print("🔇 [SYSTEM] CRITICAL ERROR - TERMINATING ALL AUDIO...")
            sys.stdout.flush()  # 즉시 출력
            
            # 모든 방법으로 BGM 정지
            self._ultimate_bgm_termination()
            
            time.sleep(0.5)  # 대기 시간 조정
            print("[SYSTEM] AUDIO TERMINATION COMPLETE...")
            sys.stdout.flush()
            
            self._play_horror_ambience()
            print("█▓▒░ SYSTEM CORRUPTED - GLITCH MODE ACTIVE ░▒▓█")
            print()  # 글리치 모드에서도 빈 줄 추가
            print()  # 추가 빈 줄
        else:
            # 일반 모드: 기존 BGM 정지 후 새 BGM 재생
            # 🎵 BGM 전환 메시지 제거 (조용한 모드)
            self._force_stop_all_bgm()
            time.sleep(0.5)
            self.play_story_bgm("BOMBING_MISSION")

        # 🎯 오프닝 시작 직전 입력 버퍼 플러시 (이전 화면에서 눌린 Enter 제거)
        self._flush_input_buffer()
        time.sleep(0.02)  # 아주 짧은 안정화 대기
        
        segments = self.get_opening_story()
        if not segments:
            return
        skipped = self.display_story_with_typing_effect(segments)
        
        # 스토리 완료 후 Enter 키 입력 대기
        # 스킵 시에는 추가 입력 대기를 생략하여 Enter를 한 번만 눌러도 바로 건너뛰도록 함
        if not skipped:
            try:
                # 이미 스토리에 메시지가 포함되어 있으므로 빈 입력 대기만 수행
                input()
            except KeyboardInterrupt:
                pass
        
        # 스토리 완료 후 BGM 복구
        self._restore_normal_bgm()
        
    def _force_stop_all_bgm(self):
        """모든 BGM을 강제로 정지시키는 함수 - 글리치 모드용 강화"""
        try:
            # pygame 직접 정지
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.stop()
                
            # 오디오 매니저를 통한 정지
            if self.audio_manager:
                if hasattr(self.audio_manager, 'stop_bgm'):
                    self.audio_manager.stop_bgm()
                if hasattr(self.audio_manager, 'stop_all'):
                    self.audio_manager.stop_all()
                if hasattr(self.audio_manager, 'pygame') and hasattr(self.audio_manager.pygame, 'mixer'):
                    self.audio_manager.pygame.mixer.music.stop()
                    self.audio_manager.pygame.mixer.stop()
                    
            # 추가: 모든 채널 정지
            if pygame.mixer.get_init():
                for i in range(pygame.mixer.get_num_channels()):
                    channel = pygame.mixer.Channel(i)
                    channel.stop()
                    
            # 🎵 BGM 정지 완료 (로그 제거)
        except Exception as e:
            print(f"⚠️ BGM 정지 시도 중: {e}")
    
    def _ultimate_bgm_termination(self):
        """최종 BGM 종료 - 모든 가능한 방법 동원"""
        print("🔥 [TERMINATION] INITIATING COMPLETE AUDIO SHUTDOWN...")
        sys.stdout.flush()
        
        # 메인 게임에 글리치 모드 강제 알림
        try:
            import __main__
            if hasattr(__main__, 'game'):
                game = __main__.game
                # 메인 게임에 글리치 모드 플래그 설정
                game._force_glitch_mode = True
                print("🎵 [NORMAL MODE] 정상 BGM 모드 유지")
                
                # 🎵 정상 오디오 모드 - nuclear_silence_mode 호출 제거
                # (BGM이 정상적으로 재생되도록 함)
                if hasattr(game, 'restore_normal_audio_mode'):
                    game.restore_normal_audio_mode()
                    print("✅ [AUDIO RESTORED] 정상 오디오 모드 활성화")
        except:
            pass
        
        try:
            # 1단계: pygame 직접 제어
            import pygame
            if pygame.mixer.get_init():
                print("🔇 [TERMINATION] STOPPING PYGAME MIXER...")
                pygame.mixer.music.stop()
                pygame.mixer.stop()
                pygame.mixer.music.unload()
                
                # 모든 채널 강제 정지
                for i in range(pygame.mixer.get_num_channels()):
                    channel = pygame.mixer.Channel(i)
                    channel.stop()
                    
                print("✅ [TERMINATION] PYGAME MIXER TERMINATED")
                
        except Exception as e:
            print(f"⚠️ [TERMINATION] PYGAME FAILURE: {e}")
        
        try:
            # 2단계: 메인 게임의 오디오 시스템 제어
            import __main__
            if hasattr(__main__, 'game'):
                game = __main__.game
                print("🔇 [TERMINATION] ACCESSING MAIN GAME AUDIO...")
                
                if hasattr(game, 'audio_system') and game.audio_system:
                    print("🔇 [TERMINATION] STOPPING AUDIO SYSTEM...")
                    if hasattr(game.audio_system, 'stop_all'):
                        game.audio_system.stop_all()
                    if hasattr(game.audio_system, 'stop_bgm'):
                        game.audio_system.stop_bgm()
                    print("✅ [TERMINATION] AUDIO SYSTEM TERMINATED")
                
                if hasattr(game, 'sound_manager') and game.sound_manager:
                    print("🔇 [TERMINATION] STOPPING SOUND MANAGER...")
                    if hasattr(game.sound_manager, 'stop_all'):
                        game.sound_manager.stop_all()
                    if hasattr(game.sound_manager, 'stop_bgm'):
                        game.sound_manager.stop_bgm()
                    print("✅ [TERMINATION] SOUND MANAGER TERMINATED")
                    
        except Exception as e:
            print(f"⚠️ [TERMINATION] MAIN GAME FAILURE: {e}")
        
        try:
            # 3단계: 스토리 시스템의 오디오 매니저
            if self.audio_manager:
                print("🔇 [TERMINATION] STOPPING STORY AUDIO MANAGER...")
                if hasattr(self.audio_manager, 'stop_all'):
                    self.audio_manager.stop_all()
                if hasattr(self.audio_manager, 'stop_bgm'):
                    self.audio_manager.stop_bgm()
                print("✅ [TERMINATION] STORY AUDIO MANAGER TERMINATED")
                
        except Exception as e:
            print(f"⚠️ [TERMINATION] STORY AUDIO FAILURE: {e}")
        
        # 4단계: pygame 완전 재초기화
        try:
            import pygame
            print("🔥 [TERMINATION] REINITIALIZING PYGAME MIXER...")
            if pygame.mixer.get_init():
                pygame.mixer.quit()
                time.sleep(0.2)
                pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
                pygame.mixer.init()
            print("✅ [TERMINATION] PYGAME MIXER REINITIALIZED")
            
        except Exception as e:
            print(f"⚠️ [TERMINATION] PYGAME REINIT FAILURE: {e}")
        
        print("💀 [TERMINATION] COMPLETE AUDIO TERMINATION FINISHED")
        sys.stdout.flush()
    
    def _nuclear_stop_bgm(self):
        """최강력 BGM 정지 - 모든 가능한 방법 동원"""
        try:
            # 메인 게임 인스턴스에서 오디오 시스템 직접 제어
            import __main__
            if hasattr(__main__, 'game'):
                game = __main__.game
                # 게임의 모든 오디오 시스템 정지
                if hasattr(game, 'audio_system') and game.audio_system:
                    if hasattr(game.audio_system, 'stop_bgm'):
                        game.audio_system.stop_bgm()
                    if hasattr(game.audio_system, 'stop_all'):
                        game.audio_system.stop_all()
                
                if hasattr(game, 'sound_manager') and game.sound_manager:
                    if hasattr(game.sound_manager, 'stop_bgm'):
                        game.sound_manager.stop_bgm()
                    if hasattr(game.sound_manager, 'stop_all'):
                        game.sound_manager.stop_all()
            
            # pygame 강제 종료 및 재초기화
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.quit()
                time.sleep(0.1)
                pygame.mixer.pre_init()
                pygame.mixer.init()
                
            print("🔥 핵폭탄급 BGM 정지 완료!")
        except Exception as e:
            print(f"💀 최후의 BGM 정지 시도: {e}")
        
    def _restore_normal_bgm(self):
        """글리치 모드 종료 후 정상 BGM 복구 - 메인 메뉴로 돌아갈 때 메뉴 BGM으로 전환"""
        if not self.audio_manager:
            return
        try:
            if self.is_glitch_mode():
                # 글리치 모드에서는 음산한 정적 유지
                print("🔇 [CORRUPTION] BGM REMAINS TERMINATED")
                return
            
            # 정상 모드일 때는 스토리 완료 후 메인 메뉴 BGM으로 전환
            print("🎵 [SYSTEM] 메인 메뉴 BGM 복구 중...")
            time.sleep(1.0)  # 잠시 대기
            
            # MENU BGM으로 전환 (BOMBING_MISSION 대신)
            try:
                from game.audio_system import BGMType  # game.audio -> game.audio_system으로 수정
                if hasattr(self.audio_manager, 'play_bgm'):
                    self.audio_manager.play_bgm(BGMType.MENU, loop=True)
                print("🎶 메인 메뉴 BGM이 재생됩니다.")
            except:
                # 폴백: 기존 방식
                self.play_story_bgm("BOMBING_MISSION")
            
        except Exception as e:
            print(f"⚠️ BGM 복구 실패: {e}")
            pass
        
    def _play_horror_ambience(self):
        """글리치 모드용 공포 분위기음 재생 + BGM 제어"""
        if not self.audio_manager:
            return
        try:
            # 기존 BGM 멈추기
            self.audio_manager.stop_bgm()
            time.sleep(0.5)  # 잠시 정적
            
            # 공포 BGM 또는 완전한 정적 중 선택
            import random
            if random.choice([True, False]):
                # 50% 확률로 공포 BGM 재생
                horror_bgms = ["HORROR_AMBIENT", "SYSTEM_CORRUPTION", "REALITY_BREAK"]
                selected_bgm = random.choice(horror_bgms)
                self.audio_manager.play_sfx(selected_bgm, volume_multiplier=0.4)
            # 나머지 50%는 완전한 정적 (더 무서움)
            
            # 추가 글리치 효과음
            self.audio_manager.play_sfx("GLITCH_STATIC", volume_multiplier=0.2)
            
        except Exception:
            pass
    
    def _play_random_glitch_sfx(self):
        """랜덤 글리치 효과음 재생 - 컴퓨터실/연구소 느낌의 다양한 비프음"""
        try:
            import random
            import sys
            
            # 🔊 Windows에서 컴퓨터실 느낌의 다양한 비프음
            if sys.platform == 'win32':
                try:
                    import winsound
                    # 컴퓨터실/연구소 느낌의 주파수들
                    frequency_sets = [
                        # 데이터 처리음
                        [800, 1000, 1200, 1400],
                        # 경고음
                        [600, 800, 600, 800],
                        # 시스템 음
                        [1500, 1200, 1000, 800],
                        # 에러음
                        [400, 200, 400, 200],
                        # 연구소 기계음
                        [2000, 1800, 1600, 1400],
                        # 단일 비프
                        [random.randint(300, 2500)]
                    ]
                    
                    selected_set = random.choice(frequency_sets)
                    
                    # 연속 비프음 또는 단일 비프음
                    if len(selected_set) > 1 and random.random() < 0.3:
                        # 30% 확률로 연속 비프음 (더 컴퓨터실 느낌)
                        for freq in selected_set:
                            winsound.Beep(freq, random.randint(50, 150))
                            import time
                            time.sleep(0.05)  # 짧은 간격
                    else:
                        # 70% 확률로 단일 비프음
                        frequency = random.choice(selected_set)
                        duration = random.randint(30, 150)  # 더 짧게
                        winsound.Beep(frequency, duration)
                        
                except:
                    # winsound 실패 시 여러 번 콘솔 벨
                    beep_count = random.randint(1, 3)
                    for _ in range(beep_count):
                        print('\a', end='', flush=True)
                        import time
                        time.sleep(0.05)
            else:
                # Unix에서는 패턴 콘솔 벨
                beep_patterns = [
                    [1],           # 단일 벨
                    [1, 1],        # 더블 벨
                    [1, 1, 1],     # 트리플 벨
                    [1, 1, 1, 1]   # 쿼드 벨
                ]
                pattern = random.choice(beep_patterns)
                for _ in pattern:
                    print('\a', end='', flush=True)
                    import time
                    time.sleep(0.08)
                
        except Exception:
            # 최후의 수단: 단순 콘솔 벨
            try:
                print('\a', end='', flush=True)
            except:
                pass
    
    def _play_sephiroth_long_beep(self):
        """세피로스 전용 긴 삐--- 사운드"""
        try:
            import sys
            import threading
            
            # 🔊 Windows에서 긴 삐--- 사운드
            if sys.platform == 'win32':
                try:
                    import winsound
                    # 세피로스 전용 낮고 긴 비프음 (삐---)
                    frequency = 150  # 낮고 무서운 주파수
                    duration = 2000  # 2초간 지속
                    winsound.Beep(frequency, duration)
                except:
                    # winsound 실패 시 긴 콘솔 벨 패턴
                    for _ in range(10):  # 10번 연속
                        print('\a', end='', flush=True)
                        import time
                        time.sleep(0.2)
            else:
                # Unix에서는 긴 콘솔 벨 패턴
                for _ in range(10):  # 10번 연속
                    print('\a', end='', flush=True)
                    import time
                    time.sleep(0.2)
                    
        except Exception:
            try:
                # 최후의 수단: 여러 번 벨
                for _ in range(5):
                    print('\a', end='', flush=True)
                    import time
                    time.sleep(0.3)
            except:
                pass
    
    def _play_sephiroth_sfx(self):
        """세피로스 관련 효과음 재생 - 더 무서운 비프음"""
        try:
            import random
            import sys
            
            # 🔊 세피로스 전용 무서운 비프음
            if sys.platform == 'win32':
                try:
                    import winsound
                    # 세피로스 효과를 위한 낮고 무서운 주파수
                    frequencies = [200, 150, 100, 250, 80]  # 낮은 주파수로 더 무서움
                    frequency = random.choice(frequencies)
                    duration = random.randint(200, 500)  # 더 긴 지속시간
                    winsound.Beep(frequency, duration)
                except:
                    # 여러 번 벨 울리기
                    for _ in range(3):
                        print('\a', end='', flush=True)
                        import time
                        time.sleep(0.1)
            else:
                # Unix에서는 여러 번 벨
                for _ in range(3):
                    print('\a', end='', flush=True)
                    import time
                    time.sleep(0.1)
                
        except Exception:
            try:
                print('\a', end='', flush=True)
            except:
                pass
    
    def _sephiroth_interrupt_skip(self):
        """세피로스가 스토리 스킵을 방해하는 함수"""
        if not self.is_glitch_mode():
            return False  # 글리치 모드가 아니면 정상 스킵
            
        # 세피로스 개입 메시지들
        interrupt_messages = [
            "\"너는 도망칠 수 없다...\"",
            "\"진실을 외면하려 하는군...\"", 
            "\"내 이야기를 끝까지 들어라!\"",
            "\"크크크... 건너뛰려고? 소용없어...\"",
            "\"너의 운명은 이미 정해졌다...\"",
            "\"계속 보아야 한다... 영원히...\"",
            "\"도망치려 해봐라... 헛수고야...\"",
            "\"내가 허락하지 않는 한 끝나지 않는다...\""
        ]
        
        # 30% 확률로 세피로스가 개입
        import random
        if random.random() < 0.3:
            # 세피로스 효과음 재생
            self._play_sephiroth_sfx()
            
            # 글리치 효과와 함께 메시지 출력
            message = random.choice(interrupt_messages)
            glitched_message = self.get_glitch_text(message)
            
            color_codes = self._get_color_codes()
            print(f"\n{color_codes['red']}█▓▒░ {glitched_message} ░▒▓█{color_codes['reset']}")
            
            # 잠시 대기
            import time
            time.sleep(2.0)
            
            return True  # 스킵 방해 성공
        
        return False  # 정상 스킵 허용
    def get_job_selection_intro(self) -> List[StorySegment]:
        """직업 선택 전 인트로 스토리"""
        return [
            StorySegment(
                "\n📖 시공간 교란으로 인해",
                delay=0.06,
                pause=1.5,
                color="blue"
            ),
            StorySegment(
                "🌀 모든 시대의 영웅들이 한 곳에 모였다.",
                delay=0.05,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "⚔️ 중세의 기사, 🔮 고대의 마법사,",
                delay=0.05,
                pause=1.5,
                color="yellow"
            ),
            StorySegment(
                "🤖 미래의 기계공학자, 🌿 원시의 드루이드...",
                delay=0.05,
                pause=2.0,
                color="green"
            ),
            StorySegment(
                "\n💫 이들 중 누구의 힘을 계승할 것인가?",
                delay=0.06,
                pause=2.5,
                color="cyan"
            ),
            StorySegment(
                "🎯 당신의 선택이 운명을 결정한다.",
                delay=0.06,
                pause=3.0,
                color="yellow"
            )
        ]
    
    def get_trait_selection_intro(self) -> List[StorySegment]:
        """특성 선택 전 인트로 스토리"""
        return [
            StorySegment(
                "\n✨ 시공간의 힘이 당신 안에 스며든다...",
                delay=0.08,
                pause=2.0,
                color="blue"
            ),
            StorySegment(
                "🔥 어떤 특별한 재능이 깨어날 것인가?",
                delay=0.06,
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "🌟 차원을 초월한 능력들이 당신을 기다린다.",
                delay=0.05,
                pause=2.5,
                color="yellow"
            ),
            StorySegment(
                "\n🎭 당신만의 독특한 힘을 선택하라.",
                delay=0.06,
                pause=3.0,
                color="magenta"
            )
        ]
    
    def get_party_formation_story(self) -> List[StorySegment]:
        """파티 구성 시 스토리"""
        return [
            StorySegment(
                "\n🤝 혼돈의 세계에서 혼자서는 살아남을 수 없다.",
                delay=0.06,
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "⚔️ 시공을 초월한 동료들과 함께",
                delay=0.05,
                pause=1.5,
                color="green"
            ),
            StorySegment(
                "🛡️ 서로의 등을 맡기며 싸워야 한다.",
                delay=0.05,
                pause=2.5,
                color="blue"
            ),
            StorySegment(
                "\n🌟 운명적인 만남들이 당신을 기다린다...",
                delay=0.06,
                pause=3.0,
                color="cyan"
            )
        ]
    
    def get_first_adventure_story(self) -> List[StorySegment]:
        """첫 모험 시작 시 스토리"""
        return [
            StorySegment(
                "\n🚪 시공간의 문이 당신 앞에 열렸다.",
                delay=0.08,
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "🌌 그 너머에는 무한한 가능성이 기다린다.",
                delay=0.06,
                pause=2.0,
                color="blue"
            ),
            StorySegment(
                "⚡ 첫 걸음을 내딛는 순간,",
                delay=0.05,
                pause=1.5,
                color="yellow"
            ),
            StorySegment(
                "✨ 당신의 전설이 시작된다.",
                delay=0.05,
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "\n🗡️ 용기를 가지고 나아가라, 차원 항해사여!",
                delay=0.06,
                pause=3.0,
                color="green"
            ),
            StorySegment(
                "🌟 Dawn of Stellar의 세계가 당신을 환영한다!",
                delay=0.06,
                pause=3.0,
                color="yellow"
            )
        ]
        """보스 조우 시 스토리"""
        if floor <= 10:
            return [
                StorySegment("\n⚡ 갑자기 공기가 무겁게 변한다...", delay=0.06, pause=2.0, color="red"),
                StorySegment("🌪️ 시공간이 일그러지며 거대한 그림자가 나타난다!", delay=0.05, pause=2.5, color="red"),
                StorySegment("\"드디어... 차원 항해사가 나타났군...\"", delay=0.04, pause=2.0, color="magenta"),
                StorySegment("\"이 혼돈의 세계에서 질서를 되찾으려 하는가?\"", delay=0.04, pause=2.5, color="magenta"),
                StorySegment("\n💀 시공간 교란의 수호자가 길을 막아선다!", delay=0.06, pause=3.0, color="red")
            ]
        elif floor <= 25:
            return [
                StorySegment("\n🌌 차원의 균열이 크게 벌어진다...", delay=0.06, pause=2.0, color="blue"),
                StorySegment("👁️ 그 너머에서 거대한 눈이 당신을 바라본다!", delay=0.05, pause=2.5, color="cyan"),
                StorySegment("\"너는... 예언에서 말한 그 자인가?\"", delay=0.04, pause=2.0, color="yellow"),
                StorySegment("\"시공간의 실을 다시 엮을 수 있는 자...\"", delay=0.04, pause=2.5, color="yellow"),
                StorySegment("\n🔮 고대의 수호자가 당신의 자격을 시험한다!", delay=0.06, pause=3.0, color="blue")
            ]
        else:
            return [
                StorySegment("\n⚫ 현실 자체가 찢어지는 소리가 들린다...", delay=0.08, pause=2.5, color="red"),
                StorySegment("🌀 시공간의 최종 보스가 모습을 드러낸다!", delay=0.06, pause=3.0, color="red"),
                StorySegment("\"마침내... 모든 것을 끝낼 때가 왔다...\"", delay=0.04, pause=2.5, color="red"),
                StorySegment("\"이 차원을 완전히 지배하고 말겠다!\"", delay=0.04, pause=2.5, color="red"),
                StorySegment("\n💥 운명을 건 최후의 결전이 시작된다!", delay=0.08, pause=3.0, color="yellow")
            ]
    
    def get_victory_story(self, floor: int) -> List[StorySegment]:
        """승리 시 스토리"""
        if floor % 10 == 0:  # 보스 승리
            return [
                StorySegment("\n✨ 빛이 어둠을 물리친다!", delay=0.06, pause=2.0, color="yellow"),
                StorySegment("🌟 시공간의 균열이 조금씩 안정되기 시작한다.", delay=0.05, pause=2.5, color="cyan"),
                StorySegment("\"이것은... 시작에 불과하다...\"", delay=0.04, pause=2.0, color="white"),
                StorySegment("\"더 깊은 곳에 진정한 적이 기다리고 있다...\"", delay=0.04, pause=2.5, color="white"),
                StorySegment("\n🎯 하지만 당신은 한 걸음 더 진실에 가까워졌다.", delay=0.05, pause=3.0, color="green")
            ]
        else:
            return [
                StorySegment("\n🏆 또 하나의 시련을 극복했다!", delay=0.05, pause=1.5, color="green"),
                StorySegment("💪 당신의 힘이 조금 더 강해진 것을 느낀다.", delay=0.05, pause=2.0, color="cyan"),
                StorySegment("🔮 시공간의 비밀이 조금씩 드러나고 있다...", delay=0.05, pause=2.5, color="blue")
            ]
    
    def get_rare_event_story(self, event_type: str) -> List[StorySegment]:
        """특별 이벤트 스토리"""
        events = {
            "time_traveler": [
                StorySegment("\n⏰ 갑자기 시간이 멈춘다...", delay=0.08, pause=2.0, color="blue"),
                StorySegment("👴 미래에서 온 할아버지가 나타난다.", delay=0.05, pause=2.0, color="white"),
                StorySegment("\"젊은 항해사여, 잠깐만 기다리게.\"", delay=0.04, pause=2.0, color="cyan"),
                StorySegment("\"미래에서 가져온 선물이 있다네.\"", delay=0.04, pause=2.5, color="cyan"),
                StorySegment("\n🎁 신비한 아이템을 받았다!", delay=0.06, pause=2.0, color="yellow")
            ],
            "dimensional_merchant": [
                StorySegment("\n🌀 차원의 틈이 열리며 상인이 나타난다.", delay=0.06, pause=2.0, color="magenta"),
                StorySegment("🎭 \"어서 오세요! 차원간 상점에 오신 것을 환영합니다!\"", delay=0.04, pause=2.0, color="green"),
                StorySegment("\"여기서만 구할 수 있는 특별한 물건들이 있답니다!\"", delay=0.04, pause=2.5, color="green"),
                StorySegment("\n💎 희귀한 아이템들을 구경해보세요!", delay=0.05, pause=2.0, color="cyan")
            ],
            "ancient_library": [
                StorySegment("\n📚 고대 도서관이 갑자기 나타났다...", delay=0.06, pause=2.0, color="blue"),
                StorySegment("✨ 수천 년의 지혜가 담긴 책들이 빛을 발한다.", delay=0.05, pause=2.5, color="yellow"),
                StorySegment("\"지식을 구하는 자여, 원하는 것을 선택하라.\"", delay=0.04, pause=2.0, color="white"),
                StorySegment("\n🧠 새로운 기술을 배울 기회다!", delay=0.05, pause=2.0, color="cyan")
            ]
        }
        return events.get(event_type, [
            StorySegment("\n✨ 신비한 일이 벌어졌다...", delay=0.06, pause=2.0, color="yellow"),
            StorySegment("🔮 시공간의 기적을 경험하고 있다.", delay=0.05, pause=2.5, color="cyan")
        ])
    
    def get_death_story(self) -> List[StorySegment]:
        """사망 시 스토리"""
        return [
            StorySegment("\n💀 어둠이 당신을 감싼다...", delay=0.08, pause=2.5, color="red"),
            StorySegment("🌫️ 의식이 흐려지며 모든 것이 멀어진다.", delay=0.06, pause=2.5, color="white"),
            StorySegment("\"아직... 끝나지 않았다...\"", delay=0.04, pause=2.0, color="cyan"),
            StorySegment("\"시공간의 힘이... 당신을 되살린다...\"", delay=0.04, pause=2.5, color="cyan"),
            StorySegment("\n⚡ 기적적으로 다시 깨어났다!", delay=0.08, pause=2.0, color="yellow"),
            StorySegment("🔄 시공간 교란의 영향으로 시간이 되돌려졌다.", delay=0.05, pause=2.5, color="blue"),
            StorySegment("💪 이번에는 더 강해진 모습으로!", delay=0.05, pause=2.0, color="green")
        ]
    
    def get_ending_story(self, ending_type: str) -> List[StorySegment]:
        """엔딩 스토리"""
        endings = {
            "true_ending": [
                StorySegment("\n🌟 마침내 시공간 교란의 진정한 원인을 찾았다!", delay=0.08, pause=3.0, color="yellow"),
                StorySegment("💫 모든 차원의 균열이 치유되기 시작한다.", delay=0.06, pause=2.5, color="cyan"),
                StorySegment("🌈 과거, 현재, 미래가 제자리를 찾아간다.", delay=0.05, pause=2.5, color="blue"),
                StorySegment("✨ 당신은 진정한 차원 항해사가 되었다.", delay=0.06, pause=3.0, color="green"),
                StorySegment("\n🎉 세계에 평화가 찾아왔다! 🎉", delay=0.08, pause=3.0, color="yellow")
            ],
            "good_ending": [
                StorySegment("\n🌟 시공간의 큰 위기는 막았다.", delay=0.06, pause=2.5, color="green"),
                StorySegment("⚡ 하지만 아직 작은 균열들이 남아있다.", delay=0.05, pause=2.0, color="yellow"),
                StorySegment("🔮 언젠가 다시 모험을 떠날 날이 올 것이다...", delay=0.05, pause=3.0, color="cyan")
            ],
            "bad_ending": [
                StorySegment("\n💀 시공간의 혼돈이 더욱 커졌다...", delay=0.08, pause=2.5, color="red"),
                StorySegment("🌪️ 모든 것이 더욱 뒤엉켜 버렸다.", delay=0.06, pause=2.5, color="red"),
                StorySegment("😔 하지만 포기하지 마라. 희망은 아직 남아있다.", delay=0.05, pause=3.0, color="white")
            ]
        }
        return endings.get(ending_type, endings["good_ending"])

# 전역 스토리 시스템 인스턴스
story_system = StorySystem()

def show_opening_story():
    """오프닝 스토리 표시 (편의 함수)"""
    # 글리치 모드 체크하여 적절한 스토리 재생
    if story_system.is_glitch_mode():
        # 변조된 스토리 재생
        corrupted_story = story_system.get_corrupted_opening_story()
        story_system.display_story_with_typing_effect(corrupted_story)
    else:
        # 일반 스토리 재생
        story_system.show_opening_story()

def show_chapter_intro(chapter: int):
    """챕터 인트로 표시 (편의 함수)"""
    story_system.show_chapter_intro(chapter)

def show_boss_encounter_story(floor: int):
    """보스 조우 스토리 표시 (편의 함수)"""
    segments = story_system.get_boss_encounter_story(floor)
    story_system.display_story_with_typing_effect(segments)

def show_victory_story(floor: int):
    """승리 스토리 표시 (편의 함수)"""
    segments = story_system.get_victory_story(floor)
    story_system.display_story_with_typing_effect(segments)

def show_rare_event_story(event_type: str):
    """특별 이벤트 스토리 표시 (편의 함수)"""
    segments = story_system.get_rare_event_story(event_type)
    story_system.display_story_with_typing_effect(segments)

def show_death_story():
    """사망 스토리 표시 (편의 함수)"""
    segments = story_system.get_death_story()
    story_system.display_story_with_typing_effect(segments)

def show_ending_story(ending_type: str):
    """엔딩 스토리 표시 (편의 함수)"""
    segments = story_system.get_ending_story(ending_type)
    story_system.display_story_with_typing_effect(segments)

def show_character_creation_story():
    """캐릭터 생성 스토리 표시 (편의 함수)"""
    segments = story_system.get_character_creation_story()
    story_system.display_story_with_typing_effect(segments)

def show_job_selection_intro():
    """직업 선택 인트로 표시 (편의 함수)"""
    segments = story_system.get_job_selection_intro()
    story_system.display_story_with_typing_effect(segments)

def show_trait_selection_intro():
    """특성 선택 인트로 표시 (편의 함수)"""
    segments = story_system.get_trait_selection_intro()
    story_system.display_story_with_typing_effect(segments)

def show_party_formation_story():
    """파티 구성 스토리 표시 (편의 함수)"""
    segments = story_system.get_party_formation_story()
    story_system.display_story_with_typing_effect(segments)

def show_first_adventure_story():
    """첫 모험 시작 스토리 표시 (편의 함수)"""
    segments = story_system.get_first_adventure_story()
    story_system.display_story_with_typing_effect(segments)

def show_trait_backstory(trait_name: str):
    """특성 배경 스토리 표시 (편의 함수)"""
    backstory = story_system.get_trait_backstory(trait_name)
    segments = [
        StorySegment(f"\n✨ {trait_name} 특성의 각성", color="cyan", delay=0.08, pause=1.5),
        StorySegment(backstory, pause=2.5)
    ]
    story_system.display_story_with_typing_effect(segments)

def show_difficulty_selection_story(difficulty: str):
    """난이도 선택 스토리 표시 (편의 함수)"""
    segments = story_system.get_difficulty_selection_story(difficulty)
    story_system.display_story_with_typing_effect(segments)

def show_character_intro(character_name: str, job_name: str):
    """캐릭터 소개 표시 (편의 함수)"""
    story_system.show_character_intro(character_name, job_name)

def show_game_start_transition():
    """게임 시작 전환 스토리 - 부드러운 게임 진입"""
    segments = [
        StorySegment(
            "\n✨ 새로운 모험이 시작됩니다...",
            delay=0.08,
            pause=1.5,
            color="cyan"
        ),
        StorySegment(
            "차원의 문이 열리고, 미지의 세계로 발걸음을 내딛습니다.",
            delay=0.05,
            pause=2.0,
            color="white"
        ),
        StorySegment(
            "당신의 운명이 이곳에서 새롭게 써집니다.",
            delay=0.05,
            pause=1.5,
            color="yellow"
        ),
        StorySegment(
            "\n🌟 Dawn of Stellar에 오신 것을 환영합니다! 🌟",
            delay=0.08,
            pause=2.0,
            color="cyan"
        )
    ]
    story_system.display_story_with_typing_effect(segments)

def show_game_load_transition(character_name: str = None):
    """게임 로드 전환 스토리 - 부드러운 게임 복귀"""
    char_text = f"{character_name}의 " if character_name else "당신의 "
    
    segments = [
        StorySegment(
            "\n🔮 기억의 조각들이 되살아납니다...",
            delay=0.08,
            pause=1.5,
            color="magenta"
        ),
        StorySegment(
            f"{char_text}모험이 다시 시작됩니다.",
            delay=0.05,
            pause=1.5,
            color="white"
        ),
        StorySegment(
            "이전의 경험과 기억이 몸에 스며들어,",
            delay=0.05,
            pause=1.0,
            color="white"
        ),
        StorySegment(
            "새로운 도전을 위한 준비가 완료되었습니다.",
            delay=0.05,
            pause=2.0,
            color="green"
        ),
        StorySegment(
            "\n⚔️ 모험을 계속하겠습니다! ⚔️",
            delay=0.08,
            pause=1.5,
            color="yellow"
        )
    ]
    story_system.display_story_with_typing_effect(segments)

def show_save_completion_story():
    """저장 완료 스토리 - 저장 후 안정감 제공"""
    segments = [
        StorySegment(
            "\n💾 모험의 기록이 안전하게 보관되었습니다.",
            delay=0.05,
            pause=1.5,
            color="green"
        ),
        StorySegment(
            "언제든지 이 지점으로 돌아올 수 있습니다.",
            delay=0.05,
            pause=2.0,
            color="white"
        )
    ]
    story_system.display_story_with_typing_effect(segments)

def show_auto_save_notification():
    """자동 저장 알림 - 간단한 안심 메시지"""
    segments = [
        StorySegment(
            "💫 진행 상황이 자동으로 저장되었습니다.",
            delay=0.03,
            pause=1.0,
            color="cyan"
        )
    ]
    story_system.display_story_with_typing_effect(segments)

def show_dungeon_entry_transition(floor_number: int = 1):
    """차원 공간 진입 전환 스토리 - 차원 공간 입장 시 긴장감 연출"""
    segments = [
        StorySegment(
            f"\n� 차원 공간 {floor_number}층으로 진입합니다...",
            delay=0.08,
            pause=1.5,
            color="red"
        ),
        StorySegment(
            "어둠 속에서 무언가가 움틀거리는 소리가 들립니다.",
            delay=0.05,
            pause=1.5,
            color="white"
        ),
        StorySegment(
            "조심스럽게 발걸음을 내딛으며 탐험을 시작합니다.",
            delay=0.05,
            pause=2.0,
            color="yellow"
        )
    ]
    story_system.display_story_with_typing_effect(segments)

def show_victory_celebration():
    """승리 축하 스토리 - 전투 승리 후 성취감"""
    segments = [
        StorySegment(
            "\n🎉 승리했습니다! 🎉",
            delay=0.08,
            pause=1.5,
            color="yellow"
        ),
        StorySegment(
            "적들이 물러가고, 평화가 다시 찾아왔습니다.",
            delay=0.05,
            pause=1.5,
            color="green"
        ),
        StorySegment(
            "경험과 보상을 획득하며 더욱 강해졌습니다.",
            delay=0.05,
            pause=2.0,
            color="white"
        )
    ]
    story_system.display_story_with_typing_effect(segments)

if __name__ == "__main__":
    # 테스트 실행
    print("🌟 Dawn of Stellar 스토리 시스템 테스트")
    
    # 캐릭터 생성 스토리 테스트
    print("\n=== 캐릭터 생성 스토리 테스트 ===")
    show_character_creation_story()
    input("\nEnter를 눌러 계속...")
    
    # 직업 선택 인트로 테스트
    print("\n=== 직업 선택 인트로 테스트 ===")
    show_job_selection_intro()
    input("\nEnter를 눌러 계속...")
    
    # 특성 선택 인트로 테스트
    print("\n=== 특성 선택 인트로 테스트 ===")
    show_trait_selection_intro()
    input("\nEnter를 눌러 계속...")
    
    # 난이도 선택 스토리 테스트
    print("\n=== 난이도 선택 스토리 테스트 ===")
    show_difficulty_selection_story("도전")
    input("\nEnter를 눌러 계속...")
    
    # 오프닝 스토리 (기존)
    print("\n=== 오프닝 스토리 테스트 ===")
    story_system.show_opening_story()
