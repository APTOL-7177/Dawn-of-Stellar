# 🔄 Dawn of Stellar - 업데이트 가이드

## 📋 업데이트 방식 선택

### 💡 권장 방식: 완전 교체 (가장 안전하고 간단)

새 버전이 출시되면 전체 게임 폴더를 교체하는 방식입니다.

### 🔧 다른 방식들
- **증분 업데이트**: 변경된 파일만 교체 (고급 사용자용)
- **자동 업데이트**: 별도 런처 프로그램 (미래 개발 예정)

---

## 🚀 완전 교체 업데이트 방법

### 1단계: 새 버전 다운로드
```
DawnOfStellar_v6.2.0.zip  # 새 버전 파일
```

### 2단계: 기존 게임 백업 (선택사항)
```bash
# 현재 게임 폴더를 백업 (예: DawnOfStellar_Old)
# user_data 폴더의 세이브 데이터가 중요함
```

### 3단계: 새 버전 압축 해제
```
DawnOfStellar_v6.2.0.zip
├── DawnOfStellar.exe    # 새 실행 파일
├── _internal/           # 업데이트된 엔진
├── config.yaml          # 새 설정 파일
├── assets/              # 새 리소스
├── data/                # 업데이트된 데이터
├── *.ttf, *.bdf         # 새 폰트
└── user_data/           # ⚠️ 비어있음 (기존 데이터 보존 필요)
```

### 4단계: 데이터 이전
```bash
# 새 버전 폴더에 기존 user_data 복사
copy "기존폴더\user_data" "새버전폴더\user_data"
```

### 5단계: 게임 실행
- 새 버전의 `DawnOfStellar.exe` 실행
- 게임이 정상 작동하는지 확인

---

## 📁 폴더 구조 비교

### 기존 버전 (v6.1.0)
```
DawnOfStellar/
├── DawnOfStellar.exe
├── _internal/
├── config.yaml
├── assets/
├── data/
├── *.ttf, *.bdf
└── user_data/           # ⭐ 플레이어 데이터
    ├── meta_progress.json
    ├── save_*.json
    └── logs/
```

### 새 버전 (v6.2.0)
```
DawnOfStellar_New/
├── DawnOfStellar.exe    # ✅ 업데이트됨
├── _internal/           # ✅ 업데이트됨
├── config.yaml          # ✅ 업데이트됨
├── assets/              # ✅ 업데이트됨
├── data/                # ✅ 업데이트됨
├── *.ttf, *.bdf         # ✅ 업데이트됨
└── user_data/           # ❌ 비어있음 (데이터 이전 필요)
```

---

## ⚠️ 중요: 데이터 보존

### 백업 필수 파일
- `user_data/meta_progress.json` - 메타 진행 상황
- `user_data/save_*.json` - 게임 세이브 파일
- `user_data/logs/` - 로그 파일 (선택사항)

### 이전 방법
```batch
# 방법 1: 수동 복사
xcopy "기존\user_data\*" "새버전\user_data\" /E /H /Y

# 방법 2: 폴더 통째 복사
copy "기존\user_data" "새버전\user_data"
```

---

## 🔍 업데이트 확인 방법

### 게임 내 확인
1. 타이틀 화면의 버전 정보 확인
2. 설정 메뉴에서 버전 확인
3. 변경 로그 확인 (게임 내 또는 웹사이트)

### 파일 버전 확인
```batch
# config.yaml에서 버전 확인
type config.yaml | findstr "version"
```

---

## 🛠️ 문제 해결

### 업데이트 후 게임이 실행되지 않음
1. **안티바이러스**: 새 파일들을 신뢰하도록 설정
2. **권한**: 게임 폴더에 실행 권한 부여
3. **데이터 호환성**: user_data 폴더가 제대로 복사되었는지 확인

### 이전 데이터가 사라짐
1. 백업본에서 user_data 복원
2. 새 버전 폴더에 user_data 폴더 수동 생성
3. 기존 세이브 파일 복사

### 그래픽/사운드 문제
1. assets 폴더가 제대로 복사되었는지 확인
2. 폰트 파일들이 모두 있는지 확인
3. config.yaml 설정 재확인

---

## 📊 업데이트 히스토리

### v6.2.0 (예시)
- ✨ 새로운 직업 추가
- 🐛 버그 수정
- 🎵 사운드 개선
- 📈 성능 최적화

### v6.1.0
- 🎮 초기 배포 버전

---

## 💡 팁

### 자동 백업 스크립트
```batch
@echo off
REM update_backup.bat - 자동 백업 스크립트
if exist "DawnOfStellar_Backup" rmdir /s /q "DawnOfStellar_Backup"
xcopy "DawnOfStellar" "DawnOfStellar_Backup" /E /H /I /Y
echo 백업 완료: DawnOfStellar_Backup
```

### 업데이트 알림
- 게임 내 업데이트 알림 기능 (미래 추가 예정)
- 웹사이트/포럼에서 업데이트 공지 확인

---

**문의사항이 있으시면 개발자에게 연락해주세요!** 🚀
