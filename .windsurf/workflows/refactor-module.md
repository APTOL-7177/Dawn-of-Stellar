---
description: 대형 모듈을 리팩토링하는 워크플로우
---

# 모듈 리팩토링

## 1. 현황 파악
// turbo
대상 파일의 크기와 구조를 파악한다:
```bash
python -c "
import pathlib, sys
f = pathlib.Path(sys.argv[1])
lines = f.read_text(encoding='utf-8').splitlines()
print(f'{f.name}: {len(lines)} lines, {f.stat().st_size/1024:.0f}KB')
# 클래스/함수 목록
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if stripped.startswith('class ') or stripped.startswith('def '):
        print(f'  L{i}: {stripped[:80]}')
" <target_file>
```

대형 파일 예시:
- `gimmick_updater.py` (333KB)
- `combat_manager.py` (280KB)
- `trait_effects.py` (211KB)
- `enemy_skills.py` (186KB)

## 2. 분리 계획 수립
- 기능별 그룹핑: 관련 메서드를 하나의 모듈로 묶는다
- 의존성 분석: 모듈 간 import 방향을 확인한다
- 인터페이스 설계: 분리 후 공개 API를 정의한다

## 3. 새 모듈 생성
관련 메서드들을 새 파일로 이동한다:
- 원본 파일에서 메서드를 잘라내어 새 파일에 붙인다
- import 문을 정리한다
- 원본에서 새 모듈을 import하여 기존 인터페이스를 유지한다

## 4. 호환성 보장
- 기존 호출부가 깨지지 않도록 `__init__.py`에서 re-export 한다
- `from new_module import func` 형태로 원본에 위임(delegate)을 남긴다

## 5. 테스트
```bash
pytest tests/ -x -q
```
모든 기존 테스트가 통과하는지 확인한다.

## 6. lint 확인
// turbo
```bash
black --check src && isort --check-only src
```
