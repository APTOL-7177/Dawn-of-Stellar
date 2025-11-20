# Dawn of Stellar - 배포 가이드

## 📦 실행 파일 만들기

이 가이드는 게임을 실행 파일로 만들어 배포하는 방법을 설명합니다.

### 빠른 시작

1. **빌드 스크립트 실행**
   - Windows: `build_executable.bat` 파일을 더블클릭
   - 자동으로 필요한 패키지를 설치하고 실행 파일을 생성합니다.

2. **빌드 완료**
   - `dist` 폴더에 `DawnOfStellar.exe` 파일이 생성됩니다.
   - `dist` 폴더의 모든 내용을 다른 컴퓨터로 복사하면 Python 없이도 실행할 수 있습니다.

### 수동 빌드

명령줄에서 직접 빌드하려면:

```bash
# 1. PyInstaller 설치
pip install pyinstaller

# 2. 빌드 실행
python -m PyInstaller build.spec --clean --noconfirm
```

### 빌드 옵션 수정

`build.spec` 파일을 수정하여 빌드 옵션을 변경할 수 있습니다:

#### 콘솔 창 숨기기
```python
console=False,  # True → False로 변경
```

#### 아이콘 추가
```python
icon="경로/아이콘.ico",  # None → 아이콘 파일 경로로 변경
```

#### UPX 압축 비활성화
```python
upx=False,  # True → False로 변경 (일부 백신에서 오탐지 방지)
```

### 포함된 리소스

빌드된 실행 파일에는 다음이 포함됩니다:

- ✅ 모든 Python 라이브러리 (tcod, numpy, pygame 등)
- ✅ 게임 코드 및 데이터
- ✅ 폰트 파일 (한글 지원)
- ✅ 오디오 파일 (BGM, SFX)
- ✅ 설정 파일

### 배포 패키지 구성

배포할 때는 `dist` 폴더의 모든 내용을 포함해야 합니다:

```
DawnOfStellar/
├── DawnOfStellar.exe      # 실행 파일
├── _internal/             # 내부 라이브러리 (자동 생성)
├── config.yaml            # 설정 파일
├── data/                  # 게임 데이터
├── assets/                # 오디오 파일
├── config/                # 메타 진행 데이터
└── *.pyd, *.dll          # Python 확장 모듈
```

### 파일 크기 최적화

실행 파일 크기를 줄이려면:

1. **불필요한 패키지 제외**
   - `build.spec`의 `excludes` 리스트에 추가

2. **UPX 압축 사용**
   - `upx=True` (기본값)
   - 일부 백신에서 오탐지할 수 있으므로 주의

3. **단일 파일 모드**
   - 현재 설정은 단일 실행 파일로 빌드됩니다.
   - `--onefile` 옵션이 이미 적용되어 있습니다.

### 문제 해결

#### 빌드 실패

1. **의존성 확인**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. **경로 문제**
   - 모든 경로가 올바른지 확인
   - 상대 경로 사용 권장

3. **메모리 부족**
   - 다른 프로그램 종료 후 재시도
   - 가상 환경 사용 권장

#### 실행 파일이 작동하지 않는 경우

1. **DLL 누락**
   - Visual C++ 재배포 가능 패키지 설치 필요할 수 있음
   - https://aka.ms/vs/17/release/vc_redist.x64.exe

2. **경로 문제**
   - 실행 파일과 함께 모든 폴더가 같은 위치에 있어야 함
   - 상대 경로로 리소스를 찾기 때문

3. **로그 확인**
   - `logs/` 폴더의 로그 파일 확인

### 배포 체크리스트

배포 전 확인사항:

- [ ] 실행 파일이 정상적으로 빌드됨
- [ ] 게임이 정상적으로 실행됨
- [ ] 모든 리소스가 포함됨 (폰트, 오디오, 데이터)
- [ ] 저장/로드 기능이 작동함
- [ ] 다른 컴퓨터에서 테스트 완료
- [ ] 설치 가이드 작성 완료 (`INSTALL_GUIDE.md`)

### 추가 리소스

- **설치 가이드**: `INSTALL_GUIDE.md` 참조
- **사용자 가이드**: `README.md` 참조

---

## 🔧 고급 설정

### 커스텀 아이콘

1. `.ico` 파일 준비 (256x256 권장)
2. `build.spec`에서 `icon="경로/아이콘.ico"` 설정
3. 재빌드

### 버전 정보 추가

Windows 실행 파일에 버전 정보를 추가하려면:

1. `version_info.txt` 파일 생성
2. `build.spec`에 `version='version_info.txt'` 추가
3. 또는 PyInstaller의 `--version-file` 옵션 사용

### 코드 서명

배포 전 코드 서명을 추가하면 보안 경고를 줄일 수 있습니다:

```bash
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com DawnOfStellar.exe
```

---

## 📝 라이선스 고지

배포 시 다음을 포함해야 합니다:

- LICENSE 파일
- 의존성 라이선스 정보
- 크레딧 (사용한 오픈소스 라이브러리)

