"""
경로 유틸리티 - PyInstaller 빌드 환경 대응

PyInstaller 패키징 환경과 일반 실행 환경 모두에서
프로젝트 루트 경로를 올바르게 반환합니다.
"""

import sys
from pathlib import Path


def get_project_root() -> Path:
    """
    프로젝트 루트 경로 반환 (PyInstaller 빌드 환경 대응)

    - PyInstaller onedir 모드: exe가 _internal/ 안에 있으므로 상위 디렉토리 반환
    - PyInstaller onefile 모드: exe가 있는 디렉토리 반환
    - 일반 실행: src/core/paths.py 기준 3단계 상위 디렉토리 반환

    Returns:
        프로젝트 루트 Path 객체
    """
    if hasattr(sys, '_MEIPASS'):
        exe_path = Path(sys.executable)
        if exe_path.parent.name == '_internal':
            # onedir 모드: exe가 _internal 폴더 안에 있음
            return exe_path.parent.parent
        return exe_path.parent
    # 일반 실행: src/core/paths.py → src/core → src → project_root
    return Path(__file__).parent.parent.parent
