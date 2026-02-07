---
description: 코드 린트 및 포맷팅을 실행하는 워크플로우
---

# 코드 린트 & 포맷팅

## 1. Black 포맷팅 적용
```bash
black src tests
```

## 2. isort import 정렬
```bash
isort src tests
```

## 3. Pylint 정적 분석
```bash
pylint src
```

## 4. Mypy 타입 체크
```bash
mypy src
```

## 5. 체크만 (수정 없이)
// turbo
```bash
black --check src tests && isort --check-only src tests
```

## 6. 문제 수정
- Black/isort 문제: 자동 포맷팅으로 해결 (1~2단계)
- Pylint 경고: 코드 수정 필요. `pyproject.toml`의 `[tool.pylint]` 설정 참고
- Mypy 에러: 타입 힌트 추가. 새 함수는 반드시 타입 힌트 필수
