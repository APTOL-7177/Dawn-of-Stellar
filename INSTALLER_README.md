# Dawn of Stellar 설치 프로그램 가이드

## NSIS 설치 프로그램

이 프로젝트는 NSIS (Nullsoft Scriptable Install System)를 사용하여 Windows용 설치 프로그램을 생성할 수 있습니다.

## NSIS 설치

1. [NSIS 공식 웹사이트](https://nsis.sourceforge.io/Download)에서 NSIS를 다운로드합니다.
2. NSIS를 설치합니다.
3. 설치 후 `makensis.exe`가 PATH에 포함되어 있는지 확인합니다.

## 설치 프로그램 빌드

### 방법 1: 배치 파일 사용 (권장)

```batch
build_installer.bat
```

### 방법 2: 수동 빌드

```batch
makensis install.nsi
```

또는 NSIS가 PATH에 없는 경우:

```batch
"C:\Program Files (x86)\NSIS\makensis.exe" install.nsi
```

## 빌드 결과

빌드가 성공하면 `DawnOfStellar_Setup.exe` 파일이 생성됩니다.

## 설치 프로그램 기능

### 자동 설치 기능

1. **게임 파일 설치**
   - 모든 소스 코드
   - 데이터 파일
   - 설정 파일
   - 문서

2. **Python 환경 설정**
   - Python 설치 확인
   - pip 자동 업그레이드
   - requirements.txt 자동 설치
   - 필수 패키지 테스트

3. **바로가기 생성**
   - 시작 메뉴 바로가기
   - 바탕화면 바로가기
   - 개발 모드 바로가기

4. **Git 저장소 클론** (선택)
   - GitHub에서 최신 소스 코드 클론

### 설치 옵션

- **전체 설치 (권장)**: 모든 기능 포함
- **최소 설치**: 필수 파일만 설치

### 제거 프로그램

설치된 게임은 제어판의 "프로그램 제거"에서 제거할 수 있습니다.

## 사용자 가이드

### 설치 방법

1. `DawnOfStellar_Setup.exe`를 실행합니다.
2. 설치 마법사의 안내를 따릅니다.
3. 설치 옵션을 선택합니다:
   - 게임 파일 (필수)
   - 바로가기 (권장)
   - Python 환경 설정 (필수)
   - Git 저장소 클론 (선택)
4. 설치 디렉토리를 선택합니다 (기본: `C:\Program Files\Dawn of Stellar`).
5. 설치를 완료합니다.

### Python이 없는 경우

Python이 설치되어 있지 않으면:
1. Python 다운로드 페이지가 자동으로 열립니다.
2. Python 3.10 이상을 다운로드하여 설치합니다.
3. **중요**: 설치 시 "Add Python to PATH" 옵션을 체크하세요!
4. 설치 후 설치 프로그램을 다시 실행합니다.

### 게임 실행

설치 완료 후:
- **시작 메뉴**: 시작 메뉴에서 "Dawn of Stellar" 선택
- **바탕화면**: 바탕화면의 바로가기 더블클릭
- **수동 실행**: 설치 디렉토리에서 `start_game.bat` 실행

### 개발 모드

모든 직업이 해금된 개발 모드로 실행하려면:
- 시작 메뉴에서 "Dawn of Stellar (개발 모드)" 선택

## 문제 해결

### Python을 찾을 수 없습니다

- Python이 PATH에 추가되어 있는지 확인하세요.
- Python 설치 시 "Add Python to PATH" 옵션을 체크했는지 확인하세요.
- 수동으로 PATH에 추가하려면:
  1. 시스템 속성 > 환경 변수
  2. PATH에 Python 설치 경로 추가 (예: `C:\Python310`)

### 패키지 설치 실패

- 인터넷 연결을 확인하세요.
- 방화벽이나 보안 프로그램이 pip를 차단하지 않는지 확인하세요.
- 수동으로 설치:
  ```batch
  cd "C:\Program Files\Dawn of Stellar"
  pip install -r requirements.txt
  ```

### Git 클론 실패

- Git이 설치되어 있는지 확인하세요.
- 인터넷 연결을 확인하세요.
- 수동으로 클론:
  ```batch
  git clone https://github.com/APTOL-7177/Dawn-of-Stellar.git
  ```

## 고급 사용

### 설치 디렉토리 변경

기본 설치 디렉토리는 `C:\Program Files\Dawn of Stellar`입니다.
설치 마법사에서 다른 경로를 선택할 수 있습니다.

### 수동 설치

설치 프로그램 없이 수동으로 설치하려면:
1. 프로젝트 파일을 원하는 위치에 복사합니다.
2. 명령 프롬프트에서 해당 디렉토리로 이동합니다.
3. 다음 명령어를 실행합니다:
   ```batch
   pip install -r requirements.txt
   python main.py
   ```

## 기술 정보

- **NSIS 버전**: 3.x 이상 권장
- **Python 버전**: 3.10 이상 필수
- **관리자 권한**: 설치 시 필요
- **디스크 공간**: 약 200MB

## 라이선스

이 설치 프로그램은 MIT 라이선스 하에 배포됩니다.

