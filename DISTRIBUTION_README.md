# Dawn of Stellar - 배포 가이드

## 📦 패키징된 게임 실행 방법

### 자동 패키징
```bash
# 프로젝트 루트에서 실행
.\build_final.bat
```

이 스크립트는 자동으로:
- Python 실행 파일 빌드
- 게임 리소스 복사
- 배포 준비 완료

### 수동 실행
```bash
# 1. 빌드
python -m PyInstaller build_folder.spec --clean --noconfirm

# 2. 게임 폴더로 이동
cd dist/DawnOfStellar

# 3. 리소스 복사
copy ..\..\config.yaml config.yaml
copy ..\..\*.ttf .
copy ..\..\*.ttc .
copy ..\..\*.bdf .
xcopy ..\..\assets assets /E /I /H /Y

# 4. 실행
.\DawnOfStellar.exe
```

## 🎮 게임 실행

1. `dist/DawnOfStellar` 폴더로 이동
2. `DawnOfStellar.exe` 더블클릭
3. 게임 시작!

## 📁 폴더 구조

```
DawnOfStellar/
├── DawnOfStellar.exe      # 메인 실행 파일
├── _internal/             # Python 런타임 (자동 생성)
├── config.yaml           # 게임 설정 (모든 직업/특성 해금)
├── assets/               # 게임 리소스 (BGM, 이미지 등)
├── data/                 # 게임 데이터 (직업, 스킬, 아이템 등)
├── *.ttf, *.bdf         # 폰트 파일 (한글 지원)
└── user_data/           # 사용자 데이터 (자동 생성)
    ├── logs/            # 게임 로그
    ├── saves/           # 세이브 파일
    └── settings/        # 사용자 설정
```

## ✅ 포함된 기능

- ✅ **완전 독립 실행**: Python 설치 불필요
- ✅ **BGM/SFX 지원**: 배경음악 및 효과음
- ✅ **한글 폰트**: 한국어 텍스트 지원
- ✅ **모든 직업 33개**: 기본/고급/특별 직업 모두 해금
- ✅ **기본 특성 2개씩**: 각 직업별 핵심 특성 2개씩 제공
- ✅ **기본 패시브 8개**: HP/MP 증폭, 신속, 정밀 사격 등 기본 패시브만 제공
- ✅ **사용자 데이터**: 세이브 파일 등 안전하게 저장
- ✅ **고해상도 지원**: 모니터 해상도에 맞춰 자동 조정

## 🚀 배포 방법

1. `dist/DawnOfStellar` 폴더 전체 선택
2. 압축 (ZIP) 파일 생성
3. `DawnOfStellar_v6.1.0.zip` 등으로 배포

## 🐛 문제 해결

### 게임이 실행되지 않을 때
- 모든 파일이 같은 폴더에 있는지 확인
- antivirus 프로그램이 차단하지 않는지 확인

### 소리가 들리지 않을 때
- assets 폴더가 제대로 복사되었는지 확인
- config.yaml에 오디오 설정이 활성화되어 있는지 확인

### 폰트가 깨질 때
- 폰트 파일들이 exe 파일과 같은 폴더에 있는지 확인
- Windows 시스템 폰트를 사용하도록 자동 폴백

## 📞 지원

문제가 발생하면 로그 파일을 확인해주세요:
- `user_data/logs/` 폴더의 로그 파일들
- 게임 실행 시 콘솔 창의 오류 메시지

---

**Dawn of Stellar - 별빛의 여명**
**버전 6.1.0** 🎮✨
