# Test Command

프로젝트의 테스트를 실행합니다.

## 사용법
- 전체 테스트: `/test`
- 유닛 테스트만: `/test unit`
- 통합 테스트만: `/test integration`
- 커버리지 포함: `/test coverage`

## 실행 내용

1. **기본 테스트 실행**
```bash
pytest tests/ -v
```

2. **유닛 테스트만**
```bash
pytest tests/unit/ -v
```

3. **통합 테스트만**
```bash
pytest tests/integration/ -v
```

4. **커버리지 리포트 포함**
```bash
pytest tests/ --cov=src --cov-report=html --cov-report=term
```

## 테스트 결과 확인
- 콘솔에서 결과 확인
- HTML 리포트: `htmlcov/index.html` 열기
- 실패한 테스트가 있으면 상세 로그 표시
