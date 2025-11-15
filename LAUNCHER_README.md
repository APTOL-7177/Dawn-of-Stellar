# 🎮 Dawn of Stellar 게임 런처

## 런처 버전

### GUI 런처 (v2.0) - **추천!** ⭐
- **launcher.py** - TCOD 기반 그래픽 런처
- 게임과 동일한 스타일의 GUI 창
- 마우스 없이 키보드만으로 조작
- 메뉴 방식의 직관적인 인터페이스

### CLI 런처 (v1.0)
- **launcher_cli.py** - 터미널 기반 런처
- 텍스트 메뉴 방식
- 가벼운 실행

## 실행 방법

### Windows
```bash
# 1. GUI 런처 실행 (추천)
launcher.bat
# 또는
python launcher.py

# 2. CLI 런처 실행
python launcher_cli.py

# 3. 게임 직접 실행
start_game.bat

# 4. 개발 모드로 실행
start_game_dev.bat
```

### Linux / Mac
```bash
# 1. GUI 런처 실행
python3 launcher.py

# 2. CLI 런처 실행
python3 launcher_cli.py

# 3. 게임 직접 실행
python3 main.py

# 4. 개발 모드로 실행
python3 main.py --dev
```

## GUI 런처 조작법

- **↑↓ / K/J**: 커서 이동
- **Enter / Z**: 선택
- **ESC / X**: 뒤로 가기 / 취소

## 런처 기능

### 1. 🎮 게임 시작
- 일반 모드로 게임 시작
- 모든 직업이 정상적으로 잠겨 있음

### 2. 🔧 개발 모드
- 모든 직업 잠금 해제
- 테스트 및 개발 용도

### 3. 🐛 디버그 모드
- 상세한 로그 출력
- 문제 해결 및 디버깅 용도

### 4. 💾 세이브 파일 관리
- 세이브 파일 목록 확인
- 세이브 파일 백업
- 세이브 파일 삭제
- 세이브 파일 상세 정보 확인

### 5. 📋 로그 확인
- 최근 로그 파일 확인
- 로그 내용 보기 (마지막 50줄)
- 로그 파일 삭제
- 모든 로그 삭제

### 6. 🧪 테스트 실행
- 전체 테스트 실행
- 유닛 테스트만 실행
- 통합 테스트만 실행
- 커버리지 포함 테스트

### 7. ⚙️ 설정
- 설정 파일 확인
- 설정 파일 편집
- 설정 파일 위치 열기

### 8. ℹ️ 게임 정보
- 게임 버전 및 기본 정보
- 주요 기능 안내
- 프로젝트 구조 확인

### 9. 🔍 시스템 체크
- Python 버전 확인
- 필수 파일 확인
- 디렉토리 용량 확인
- 필수 라이브러리 확인

## 게임 실행 옵션

```bash
# 기본 실행
python main.py

# 개발 모드 (모든 직업 해금)
python main.py --dev

# 디버그 모드
python main.py --debug

# 로그 레벨 설정
python main.py --log=DEBUG

# 사용자 지정 설정 파일
python main.py --config=custom_config.yaml
```

## 디렉토리 구조

```
Dawn of Stellar/
├── launcher.py          # GUI 런처 (TCOD, v2.0) ⭐
├── launcher_cli.py      # CLI 런처 (터미널, v1.0)
├── launcher.bat         # 런처 실행 파일 (Windows)
├── start_game.bat       # 게임 직접 실행 (Windows)
├── start_game_dev.bat   # 개발 모드 실행 (Windows)
├── main.py              # 게임 메인 스크립트
├── config.yaml          # 게임 설정
├── saves/               # 세이브 파일
├── logs/                # 로그 파일
├── src/                 # 소스 코드
├── data/                # 게임 데이터
├── assets/              # 에셋
└── tests/               # 테스트
```

## 문제 해결

### 런처가 실행되지 않을 때
1. Python 3.10 이상이 설치되어 있는지 확인
2. 필수 라이브러리 설치: `pip install -r requirements.txt`
3. 시스템 체크 기능으로 문제 확인

### 게임이 실행되지 않을 때
1. 런처의 시스템 체크 기능 사용
2. 로그 파일 확인
3. 디버그 모드로 실행하여 상세 정보 확인

### 세이브 파일 문제
1. 세이브 파일 관리 메뉴에서 백업 생성
2. 손상된 세이브 파일 삭제
3. `saves/` 디렉토리 권한 확인

## 팁

- **세이브 백업**: 중요한 세이브는 정기적으로 백업하세요
- **로그 관리**: 로그 파일이 너무 많으면 주기적으로 삭제하세요
- **개발 모드**: 모든 직업을 테스트하고 싶을 때 사용하세요
- **디버그 모드**: 버그 리포트 시 디버그 로그를 첨부하세요

## 라이선스

이 런처는 Dawn of Stellar 게임과 동일한 라이선스를 따릅니다.
