"""
핫 리로드 시스템

코드 변경 시 자동으로 모듈을 재로드하는 기능
"""

import sys
import importlib
import threading
import time
from pathlib import Path
from typing import Set, Optional, Callable, List
from collections import deque

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.SYSTEM)


class CodeChangeHandler(FileSystemEventHandler):
    """파일 변경 이벤트 핸들러"""
    
    def __init__(self, hot_reload_manager):
        self.hot_reload_manager = hot_reload_manager
        self.last_modified = {}  # 중복 변경 방지
        self.debounce_delay = 0.5  # 0.5초 디바운스
        
    def on_modified(self, event):
        """파일 수정 시 호출"""
        if event.is_directory:
            return
            
        # .py 파일만 처리
        if not event.src_path.endswith('.py'):
            return
            
        # 디바운스: 짧은 시간 내 여러 변경 무시
        current_time = time.time()
        last_time = self.last_modified.get(event.src_path, 0)
        
        if current_time - last_time < self.debounce_delay:
            return
            
        self.last_modified[event.src_path] = current_time
        
        # 변경된 파일 경로 저장
        try:
            file_path = Path(event.src_path)
            if file_path.exists():
                self.hot_reload_manager._add_changed_file(file_path)
                logger.info(f"📝 파일 변경 감지: {file_path}")
        except Exception as e:
            logger.warning(f"파일 변경 처리 오류: {e}")


class HotReloadManager:
    """핫 리로드 관리자"""
    
    def __init__(self, src_dir: Optional[Path] = None, enabled: bool = True):
        """
        Args:
            src_dir: 감시할 소스 디렉토리 (기본값: 프로젝트의 src/)
            enabled: 핫 리로드 활성화 여부
        """
        self.enabled = enabled and WATCHDOG_AVAILABLE
        # src_dir가 지정되지 않으면 src/ 디렉토리 찾기
        if src_dir is None:
            # src/core/hot_reload.py -> src/
            current_file = Path(__file__)
            # src/core -> src
            self.src_dir = current_file.parent.parent
        else:
            self.src_dir = src_dir
        
        # 프로젝트 루트 (src의 부모 디렉토리)
        self.project_root = self.src_dir.parent
        
        # 변경된 파일 큐 (스레드 안전)
        self._changed_files: deque = deque()
        self._changed_files_lock = threading.Lock()
        
        # 로드된 모듈 추적
        self._loaded_modules: Set[str] = set()
        
        # 파일 감시자
        self.observer: Optional[Observer] = None
        self._observer_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 리로드 콜백 함수들
        self._reload_callbacks: List[Callable[[List[str]], None]] = []
        
        # 제외할 파일/디렉토리
        self._exclude_patterns = {
            '__pycache__',
            '.pyc',
            '.pyo',
            '.pyd',
            '.git',
            'logs',
            'saves',
            'tests',
            'archive',
            'web',
            'docs',
            'examples',
            'scripts',
        }
        
    def start(self):
        """핫 리로드 시작"""
        if not self.enabled:
            logger.info("핫 리로드 비활성화됨 (watchdog 미설치 또는 비활성화)")
            return
            
        if self._running:
            logger.warning("핫 리로드가 이미 실행 중입니다")
            return
            
        try:
            self.observer = Observer()
            handler = CodeChangeHandler(self)
            # 프로젝트 루트를 감시 (src/ 포함)
            self.observer.schedule(handler, str(self.project_root), recursive=True)
            self.observer.start()
            self._running = True
            
            logger.info(f"🔥 핫 리로드 활성화됨: {self.project_root} 감시 중")
        except Exception as e:
            logger.error(f"핫 리로드 시작 실패: {e}")
            self.enabled = False
            
    def stop(self):
        """핫 리로드 중지"""
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join(timeout=1.0)
            except Exception as e:
                logger.warning(f"핫 리로드 중지 중 오류: {e}")
            finally:
                self.observer = None
                self._running = False
                logger.info("핫 리로드 중지됨")
                
    def _add_changed_file(self, file_path: Path):
        """변경된 파일 추가 (스레드 안전)"""
        # 제외 패턴 체크
        if any(pattern in str(file_path) for pattern in self._exclude_patterns):
            return
            
        with self._changed_files_lock:
            # 절대 경로를 문자열로 저장 (중복 방지)
            file_str = str(file_path.resolve())
            if file_str not in self._changed_files:
                self._changed_files.append(file_str)
                
    def check_and_reload(self) -> List[str]:
        """
        변경된 파일 확인 및 재로드
        
        Returns:
            재로드된 모듈 이름 리스트
        """
        if not self.enabled or not self._running:
            return []
            
        changed_modules = []
        
        with self._changed_files_lock:
            if not self._changed_files:
                return []
                
            # 모든 변경된 파일 처리
            files_to_reload = list(self._changed_files)
            self._changed_files.clear()
            
        for file_path_str in files_to_reload:
            try:
                module_name = self._file_path_to_module_name(file_path_str)
                if module_name:
                    success = self._reload_module(module_name)
                    if success:
                        changed_modules.append(module_name)
            except Exception as e:
                logger.warning(f"모듈 재로드 실패 ({file_path_str}): {e}")
                
        # 리로드 콜백 호출
        if changed_modules:
            for callback in self._reload_callbacks:
                try:
                    callback(changed_modules)
                except Exception as e:
                    logger.warning(f"리로드 콜백 실행 오류: {e}")
                    
        return changed_modules
        
    def _file_path_to_module_name(self, file_path_str: str) -> Optional[str]:
        """파일 경로를 모듈 이름으로 변환"""
        try:
            file_path = Path(file_path_str)
            
            # 프로젝트 루트 기준으로 상대 경로 계산
            try:
                relative_path = file_path.relative_to(self.project_root)
            except ValueError:
                # 절대 경로로 변환 후 다시 시도
                try:
                    relative_path = file_path.resolve().relative_to(self.project_root.resolve())
                except ValueError:
                    return None
                    
            # 경로를 모듈 이름으로 변환
            # 예: src/world/exploration.py -> src.world.exploration
            parts = list(relative_path.parts)
            
            # .py 확장자 제거
            if parts[-1].endswith('.py'):
                parts[-1] = parts[-1][:-3]
            elif parts[-1].endswith('.pyc'):
                parts[-1] = parts[-1][:-4]
            else:
                return None
                
            # 모듈 이름 생성
            module_name = '.'.join(parts)
            
            # sys.modules에 있는지 확인
            if module_name in sys.modules:
                return module_name
                
            # __init__.py인 경우 부모 모듈도 체크
            if parts[-1] == '__init__':
                parent_module = '.'.join(parts[:-1])
                if parent_module in sys.modules:
                    return parent_module
                    
            return None
            
        except Exception as e:
            logger.debug(f"모듈 이름 변환 실패 ({file_path_str}): {e}")
            return None
            
    def _reload_module(self, module_name: str) -> bool:
        """모듈 재로드"""
        try:
            if module_name not in sys.modules:
                logger.debug(f"모듈이 로드되지 않음: {module_name}")
                return False
                
            # 모듈 재로드
            module = sys.modules[module_name]
            importlib.reload(module)
            
            logger.info(f"✅ 모듈 재로드됨: {module_name}")
            return True
            
        except Exception as e:
            logger.error(f"모듈 재로드 실패 ({module_name}): {e}")
            return False
            
    def add_reload_callback(self, callback: Callable[[List[str]], None]):
        """
        리로드 완료 후 호출할 콜백 함수 등록
        
        Args:
            callback: 콜백 함수 (재로드된 모듈 이름 리스트를 인자로 받음)
        """
        self._reload_callbacks.append(callback)


# 전역 핫 리로드 매니저 인스턴스
_hot_reload_manager: Optional[HotReloadManager] = None


def get_hot_reload_manager(enabled: bool = True) -> HotReloadManager:
    """핫 리로드 매니저 싱글톤 인스턴스 가져오기"""
    global _hot_reload_manager
    
    if _hot_reload_manager is None:
        _hot_reload_manager = HotReloadManager(enabled=enabled)
        
    return _hot_reload_manager


def start_hot_reload(enabled: bool = True):
    """핫 리로드 시작"""
    manager = get_hot_reload_manager(enabled=enabled)
    manager.start()


def stop_hot_reload():
    """핫 리로드 중지"""
    global _hot_reload_manager
    if _hot_reload_manager:
        _hot_reload_manager.stop()


def check_and_reload() -> List[str]:
    """변경된 파일 확인 및 재로드"""
    global _hot_reload_manager
    if _hot_reload_manager:
        return _hot_reload_manager.check_and_reload()
    return []

