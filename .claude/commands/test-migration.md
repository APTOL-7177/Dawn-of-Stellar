# /test-migration - 이식 테스트 명령어

이식된 시스템들이 정상 작동하는지 테스트합니다.

## 사용법
```
/test-migration [system_name]
```

## 옵션
- `system_name` 생략 시 전체 테스트
- 특정 시스템만 테스트: `character`, `combat`, `skills` 등

## 예시
```bash
/test-migration           # 전체 테스트
/test-migration character # Character 시스템만
/test-migration combat    # Combat 시스템만
```

---

**작업 내용:**

1. pytest를 사용하여 테스트 실행
2. 실패한 테스트 분석
3. 버그 리포트 생성
4. 자동 수정 시도 (가능한 경우)
