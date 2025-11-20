# 멀티플레이 테스트 팁

## Windows에서 테스트 실행

Windows PowerShell에서는 와일드카드 패턴이 제대로 작동하지 않을 수 있습니다.

### 방법 1: -k 옵션 사용 (권장)

```bash
# 모든 멀티플레이 테스트 실행
python -m pytest tests/ -k "multiplayer" -v

# 특정 테스트만 실행
python -m pytest tests/ -k "test_multiplayer_integration" -v
```

### 방법 2: 직접 파일 지정

```bash
python -m pytest tests/test_multiplayer_basic.py tests/test_multiplayer_integration.py tests/test_multiplayer_exploration.py tests/test_multiplayer_party.py -v
```

### 방법 3: 테스트 스크립트 사용

```bash
# 멀티플레이 테스트 전용 스크립트
python tests/run_multiplayer_tests.py
```

### 방법 4: pytest 설정 파일 활용

`pyproject.toml`에 이미 설정이 되어 있으므로:

```bash
# tests 디렉토리의 모든 테스트 실행
python -m pytest tests/ -v

# 특정 파일만 실행
python -m pytest tests/test_multiplayer_integration.py -v
```

## 문제 해결

### 와일드카드 패턴이 작동하지 않는 경우

Windows PowerShell에서는 `test_multiplayer_*.py` 같은 와일드카드가 pytest에 제대로 전달되지 않을 수 있습니다.

**해결책:**
1. `-k` 옵션 사용 (권장)
2. 직접 파일명 지정
3. 테스트 스크립트 사용

### 테스트 실행 확인

```bash
# 테스트 파일 목록 확인
python -m pytest tests/ --collect-only -k "multiplayer"

# 실행할 테스트 수 확인
python -m pytest tests/ --collect-only -k "multiplayer" | findstr "test session"
```

## 현재 테스트 상태

**멀티플레이 테스트 파일:**
- `test_multiplayer_basic.py` - 15개 테스트
- `test_multiplayer_integration.py` - 13개 테스트
- `test_multiplayer_exploration.py` - 7개 테스트
- `test_multiplayer_party.py` - 5개 테스트

**총 40개 테스트 모두 통과** ✅

