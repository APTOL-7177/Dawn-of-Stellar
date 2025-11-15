# Build Command

프로젝트를 빌드하고 배포 가능한 상태로 만듭니다.

## 사용법
- 전체 빌드: `/build`
- 빠른 빌드 (테스트 스킵): `/build quick`

## 실행 내용

### 1. 코드 품질 검사
```bash
# Type checking
mypy src/

# Linting
pylint src/

# Code formatting check
black --check src/
```

### 2. 테스트 실행
```bash
pytest tests/ --cov=src --cov-report=term
```

### 3. 문서 생성
```bash
# API 문서 생성
sphinx-build -b html docs/source docs/build
```

### 4. 패키지 빌드
```bash
# Python 패키지 빌드
python -m build

# 실행 파일 생성 (PyInstaller)
pyinstaller --onefile --name="DawnOfStellar" main.py
```

### 5. 최종 확인
- 빌드 아티팩트 확인
- 버전 정보 검증
- 설정 파일 포함 확인

## 빌드 결과
- `dist/`: 배포 파일
- `docs/build/`: 문서
- `build/`: 빌드 임시 파일

## 문제 해결
빌드 실패 시:
1. 테스트 실패 → `pytest tests/ -v`로 확인
2. Type 에러 → `mypy src/`로 확인
3. Lint 에러 → `pylint src/`로 확인
