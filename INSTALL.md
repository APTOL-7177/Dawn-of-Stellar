# Dawn of Stellar 설치 가이드

⭐ **Final Fantasy 스타일 로그라이크 RPG** ⭐

28개 직업 × ATB 전투 × AI 동료 × 멀티플레이어

---

## 🚀 원클릭 설치 (권장)

### Windows 사용자

아무것도 설치되어 있지 않아도 OK!

#### 방법 1: 완전 자동 설치 (Git + Python + 게임 모두 자동)

```batch
setup-complete.bat
```

**우클릭 → "관리자 권한으로 실행"**

이 스크립트는 다음을 모두 자동으로 처리합니다:
- ✅ Git 자동 설치 및 확인
- ✅ GitHub에서 게임 코드 다운로드 (클론)
- ✅ Python 3.11 자동 설치
- ✅ 필수 패키지 설치 (TCOD, PyYAML 등)
- ✅ 데스크톱 바로가기 생성
- ✅ 게임 즉시 실행 옵션

**설치 시간**: 약 5-10분 (인터넷 속도에 따라 다름)

---

#### 방법 2: 간단 설치 (이미 게임 파일이 있는 경우)

```batch
setup-auto.bat
```

**우클릭 → "관리자 권한으로 실행"**

이 스크립트는 다음을 처리합니다:
- ✅ Python 자동 설치 (없는 경우)
- ✅ 필수 패키지 설치
- ✅ 게임 실행

---

#### 방법 3: 최소 설치 (Python이 이미 있는 경우)

```batch
install.bat
```

더블클릭만 하면 OK (관리자 권한 불필요)

- ✅ 필수 패키지만 설치
- ✅ 빠른 설치 (1-2분)

---

## 🎮 게임 실행

설치 완료 후 다음 방법으로 실행:

### 방법 1: 바로가기 사용
```
데스크톱의 "Dawn of Stellar" 바로가기 클릭
```

### 방법 2: 배치파일 실행
```batch
run.bat
```

### 방법 3: 직접 실행
```batch
python main.py
```

### 개발자 모드 (모든 직업 잠금 해제)
```batch
python main.py --dev
```

### 디버그 모드
```batch
python main.py --debug --log=DEBUG
```

---

## 🛠️ 수동 설치 (고급 사용자)

### 1. Python 설치

**요구사항**: Python 3.10 이상

https://www.python.org/downloads/

**중요**: 설치 시 "Add Python to PATH" 체크!

### 2. Git 설치 (선택)

https://git-scm.com/download/win

### 3. 게임 다운로드

#### Git 사용
```bash
git clone https://github.com/APTOL-7177/Dawn-of-Stellar.git
cd Dawn-of-Stellar
```

#### ZIP 다운로드
GitHub에서 "Code" → "Download ZIP" → 압축 해제

### 4. 패키지 설치

#### 최소 패키지만 (권장)
```bash
pip install -r requirements-minimal.txt
```

#### 전체 패키지 (개발용)
```bash
pip install -r requirements.txt
```

### 5. 게임 실행
```bash
python main.py
```

---

## 📦 설치 파일 비교

| 파일 | 자동 설치 항목 | 권장 대상 | 관리자 권한 필요 |
|------|---------------|----------|----------------|
| `setup-complete.bat` | Git + Python + 게임 + 패키지 | 완전 초보자 | ✅ 필요 |
| `setup-auto.bat` | Python + 패키지 | 게임 파일 보유자 | ✅ 필요 |
| `install.bat` | 패키지만 | Python 보유자 | ❌ 불필요 |
| `run.bat` | 없음 (실행만) | 설치 완료자 | ❌ 불필요 |

---

## 🐧 Linux/Mac 사용자

### 1. Python 확인
```bash
python3 --version  # 3.10 이상 필요
```

### 2. 게임 다운로드
```bash
git clone https://github.com/APTOL-7177/Dawn-of-Stellar.git
cd Dawn-of-Stellar
```

### 3. 가상환경 생성 (권장)
```bash
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
```

### 4. 패키지 설치
```bash
pip install -r requirements-minimal.txt
```

### 5. 게임 실행
```bash
python3 main.py
```

---

## ❓ 문제 해결 (Troubleshooting)

### Python을 찾을 수 없습니다
**원인**: PATH 환경변수 미설정

**해결**:
1. Python 재설치 ("Add to PATH" 체크)
2. 또는 수동으로 PATH 추가:
   - 제어판 → 시스템 → 고급 시스템 설정 → 환경 변수
   - Path에 `C:\Python311` 추가

### 패키지 설치 실패
**원인**: 인터넷 연결, 방화벽, pip 문제

**해결**:
```bash
# pip 업그레이드
python -m pip install --upgrade pip

# 캐시 삭제
python -m pip cache purge

# 다시 설치
pip install -r requirements-minimal.txt
```

### TCOD 모듈을 찾을 수 없습니다
**원인**: 패키지 미설치

**해결**:
```bash
pip install tcod pyyaml numpy
```

### 게임 실행 중 오류
**원인**: 파일 손상, 설정 문제

**해결**:
1. 로그 확인: `logs/` 폴더
2. 재설치: `setup-complete.bat` 다시 실행
3. 이슈 리포트: GitHub Issues

---

## 🔧 개발자용 설치

### 전체 개발 환경
```bash
# 전체 패키지 설치 (테스트, 린터 포함)
pip install -r requirements.txt

# 코드 품질 검사
pylint src/

# 타입 체크
mypy src/

# 테스트 실행
pytest tests/ -v

# 커버리지 리포트
pytest tests/ --cov=src --cov-report=html
```

### 독립 실행 파일 빌드 (EXE)
```bash
# PyInstaller 설치
pip install pyinstaller

# 빌드 실행
python build.py

# 결과: dist/DawnOfStellar.exe
```

---

## 📋 시스템 요구사항

### 최소 사양
- **OS**: Windows 10/11, macOS 10.14+, Ubuntu 20.04+
- **CPU**: Intel Core i3 이상
- **RAM**: 4GB
- **저장공간**: 500MB
- **Python**: 3.10 이상

### 권장 사양
- **OS**: Windows 11
- **CPU**: Intel Core i5 이상
- **RAM**: 8GB
- **저장공간**: 1GB
- **Python**: 3.11

---

## 🎯 빠른 시작 (Quick Start)

### 완전 초보자 (아무것도 없음)
1. `setup-complete.bat` 우클릭 → 관리자 권한 실행
2. 5-10분 대기
3. "지금 실행하시겠습니까?" → Y
4. 게임 시작!

### Python 있음
1. `install.bat` 더블클릭
2. 1-2분 대기
3. `run.bat` 실행
4. 게임 시작!

### 개발자
1. `git clone` 저장소
2. `pip install -r requirements.txt`
3. `python main.py --dev`
4. 개발 시작!

---

## 📞 지원

- **GitHub Issues**: https://github.com/APTOL-7177/Dawn-of-Stellar/issues
- **Wiki**: https://github.com/APTOL-7177/Dawn-of-Stellar/wiki
- **문서**: `docs/` 폴더

---

## ⭐ 설치 완료 후

게임을 즐기고, 별점을 남겨주세요!

**Happy Gaming! 즐거운 플레이 되세요! 🎮✨**
