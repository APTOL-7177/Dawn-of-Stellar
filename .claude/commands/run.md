# Run Command

게임을 실행합니다.

## 사용법
- 기본 실행: `/run`
- 개발 모드: `/run dev`
- 디버그 모드: `/run debug`

## 실행 내용

1. **기본 게임 실행**
```bash
python main.py
```

2. **개발 모드로 실행**
```bash
python main.py --dev
```
- 모든 캐릭터 잠금 해제
- 디버그 정보 표시
- 빠른 테스트 기능 활성화

3. **디버그 모드로 실행**
```bash
python main.py --debug --log=DEBUG
```
- 상세한 로그 출력
- 성능 프로파일링 활성화
- 에러 추적 활성화

4. **모바일 서버 모드**
```bash
python main.py --mobile-server --port=5000
```

## 실행 전 체크사항
- Python 가상환경 활성화 확인
- 필요한 의존성 설치 확인 (`requirements.txt`)
- 설정 파일 존재 확인 (`config.yaml`)
