#!/usr/bin/env python3
"""
멀티플레이 테스트 실행 스크립트

Windows에서도 작동하는 테스트 실행 스크립트입니다.
"""

import subprocess
import sys
from pathlib import Path

# 프로젝트 루트로 이동
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_tests():
    """멀티플레이 테스트 실행"""
    test_files = [
        "tests/test_multiplayer_basic.py",
        "tests/test_multiplayer_integration.py",
        "tests/test_multiplayer_exploration.py",
        "tests/test_multiplayer_party.py",
    ]
    
    # pytest 실행
    cmd = [
        sys.executable,
        "-m", "pytest",
        "-v",
        "--tb=short"
    ] + test_files
    
    print("=" * 60)
    print("멀티플레이 테스트 실행")
    print("=" * 60)
    print(f"테스트 파일: {len(test_files)}개")
    print()
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)

