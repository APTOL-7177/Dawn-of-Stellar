---
description: 테스트를 실행하는 워크플로우
---

# 테스트 실행

## 1. 전체 테스트
```bash
pytest tests/ -ra -q --strict-markers
```

## 2. 빠른 테스트 (slow 제외)
// turbo
```bash
pytest tests/ -m "not slow" -q
```

## 3. 특정 모듈 테스트
```bash
pytest tests/ -k "<keyword>" -x -v
```
키워드 예: `combat`, `skill`, `gimmick`, `multiplayer`, `tutorial`, `damage`

## 4. 커버리지 리포트
```bash
pytest tests/ --cov=src --cov-report=term-missing
```

## 5. 멀티플레이어 테스트
```bash
python tests/run_multiplayer_tests.py
```

## 6. 실패 시 대응
- 실패한 테스트의 에러 메시지와 traceback을 분석한다.
- `pytest tests/ -k "<failed_test>" -x -v --tb=long`으로 상세 로그를 확인한다.
- 근본 원인을 파악하고 수정한다.
