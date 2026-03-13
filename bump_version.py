"""버전 자동 증가 스크립트

사용법:
    python bump_version.py          # 패치 버전 +1 (1.0.0 -> 1.0.1)
    python bump_version.py minor    # 마이너 버전 +1 (1.0.1 -> 1.1.0)
    python bump_version.py major    # 메이저 버전 +1 (1.1.0 -> 2.0.0)
"""

import sys
import re

BUMP_TYPE = sys.argv[1] if len(sys.argv) > 1 else "patch"

# config.yaml에서 현재 버전 읽기
with open("config.yaml", "r", encoding="utf-8") as f:
    config = f.read()

match = re.search(r"version:\s*(\d+)\.(\d+)\.(\d+)", config)
if not match:
    print("[오류] config.yaml에서 버전을 찾을 수 없습니다.")
    sys.exit(1)

major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
old_version = f"{major}.{minor}.{patch}"

if BUMP_TYPE == "major":
    major += 1
    minor = 0
    patch = 0
elif BUMP_TYPE == "minor":
    minor += 1
    patch = 0
else:  # patch
    patch += 1

new_version = f"{major}.{minor}.{patch}"

# 모든 버전 파일 업데이트
files_to_update = [
    ("config.yaml", rf"(version:\s*){re.escape(old_version)}", rf"\g<1>{new_version}"),
    ("src/__init__.py", rf'(__version__\s*=\s*"){re.escape(old_version)}"', rf'\g<1>{new_version}"'),
    ("src/core/config.py", rf'("game":\s*\{{"version":\s*"){re.escape(old_version)}"', rf'\g<1>{new_version}"'),
]

updated = []
for filepath, pattern, replacement in files_to_update:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            updated.append(filepath)
    except FileNotFoundError:
        pass

print(f"{old_version} -> {new_version}")
for f in updated:
    print(f"  updated: {f}")

# 새 버전을 stdout 마지막 줄에 출력 (bat에서 읽기 위함)
