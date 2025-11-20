# ⭐ Dawn of Stellar (별빛의 여명)

![Version](https://img.shields.io/badge/version-6.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

> Final Fantasy 스타일의 ATB + BRV 전투 시스템을 가진 로그라이크 RPG

[🎮 플레이하기](https://github.com/APTOL-7177/Dawn-of-Stellar/releases) | [📚 Wiki](https://github.com/APTOL-7177/Dawn-of-Stellar/wiki) | [🌐 웹사이트](https://aptol-7177.github.io/Dawn-of-Stellar/) | [🐛 버그 리포트](https://github.com/APTOL-7177/Dawn-of-Stellar/issues)

---

## 📖 목차

- [게임 소개](#-게임-소개)
- [핵심 특징](#-핵심-특징)
- [설치 및 실행](#-설치-및-실행)
- [게임플레이](#-게임플레이)
- [개발 가이드](#-개발-가이드)
- [기여하기](#-기여하기)
- [라이선스](#-라이선스)

---

## 🎮 게임 소개

**Dawn of Stellar**는 Final Fantasy의 ATB(Active Time Battle) 전투 시스템과 Dissidia의 BRV(Brave) 시스템을 결합한 독창적인 로그라이크 RPG입니다.

33개의 고유한 직업, 195개 이상의 스킬, 절차적 던전 생성, 그리고 깊이 있는 전투 시스템으로 매번 새로운 도전을 경험하세요.

### 장르
로그라이크 RPG + JRPG 퓨전

### 플랫폼
- Windows 10/11
- Linux (Ubuntu 20.04+)
- macOS (10.15+)

---

## ✨ 핵심 특징

### 🗡️ 33개 고유 직업
각 직업은 독자적인 **기믹 시스템**을 보유합니다:
- **전사**: 6단계 스탠스 시스템
- **검성**: 검기 폭발 시스템
- **시간술사**: 시간 조작 능력
- **차원술사**: 확률 조작 능력
- **흡혈귀**: 혈액 마법 시스템
- **브레이커**: BRV 파괴 특화
- ...그리고 27개 더!

### ⚔️ ATB + BRV 하이브리드 전투
```
ATB 게이지 충전 → BRV 공격으로 축적 → HP 공격으로 피해 → BREAK 보너스!
```

- **ATB 시스템**: 실시간 게이지 충전 (0-2000)
- **BRV 시스템**: 데미지 축적 후 HP 공격
- **BREAK**: 적 BRV를 0으로 만들면 보너스 데미지 + 스턴

### 🎯 195+ 스킬
- **BRV 공격**: BRV 축적 (HP 데미지 없음)
- **HP 공격**: 축적된 BRV로 HP 데미지
- **BRV+HP 공격**: 둘 다 동시에
- **서포트**: 아군 버프
- **디버프**: 적 약화
- **궁극기**: 강력한 필살기

### 🏰 절차적 던전 생성
- BSP(Binary Space Partitioning) 알고리즘
- 매번 다른 맵 구조
- 랜덤 적, 아이템, 보물 배치

### 🍳 요리 & 제작 시스템
- **52개 레시피**: 한식, 일식, 양식, 중식, 디저트
- **버프 효과**: 공격력 증가, 방어력 증가, 속도 증가
- **품질 시스템**: Poor / Normal / Good / Excellent

### 💾 메타 진행 시스템
- **별조각**: 전투 승리 시 획득
- **직업 해금**: 별조각으로 새 직업 언락
- **패시브 스킬**: 영구 강화 시스템

---

## 🚀 설치 및 실행

### 방법 1: 실행 파일 다운로드 (추천)

최신 릴리스에서 플랫폼에 맞는 파일을 다운로드하세요:

👉 **[Releases 페이지](https://github.com/APTOL-7177/Dawn-of-Stellar/releases)**

- **Windows**: `DawnOfStellar-Windows.zip`
- **Linux**: `DawnOfStellar-Linux.tar.gz`
- **macOS**: `DawnOfStellar-macOS.tar.gz`

압축 해제 후 실행:
- Windows: `DawnOfStellar.exe`
- Linux/macOS: `./DawnOfStellar`

### 방법 2: 소스 코드 실행

#### 필수 요구사항
- Python 3.10 이상
- pip

#### 설치 및 실행
```bash
# 저장소 클론
git clone https://github.com/APTOL-7177/Dawn-of-Stellar.git
cd Dawn-of-Stellar

# 의존성 설치
pip install -r requirements.txt

# 게임 실행
python main.py

# 개발 모드 (모든 직업 해금)
python main.py --dev

# 디버그 모드
python main.py --debug --log=DEBUG
```

### 방법 3: 웹 버전 (실험적)

브라우저에서 체험:
- **전투 데모**: https://aptol-7177.github.io/Dawn-of-Stellar/demo.html
- **풀 게임 시도**: https://aptol-7177.github.io/Dawn-of-Stellar/game.html

⚠️ 웹 버전은 기술적 제한으로 완전히 지원되지 않습니다.

---

## 🎯 게임플레이

### 시작하기

1. **직업 선택**: 33개 직업 중 선택 (초보자 추천: 전사, 성직자, 궁수)
2. **던전 입장**: 절차적으로 생성된 던전 탐험
3. **전투**: ATB + BRV 시스템으로 적과 전투
4. **성장**: 경험치, 장비, 별조각 획득
5. **메타 진행**: 별조각으로 새 직업 해금

### 전투 시스템

```
[ATB 게이지]
0 ─────────── 1000 ─────────── 2000
            ↑ 행동 가능

[BRV 시스템]
BRV 공격 (300) → BRV 축적 → HP 공격 → 실제 데미지!
             ↓
        적 BRV = 0
             ↓
        BREAK! (+50% 보너스)
```

### 조작법

| 키 | 기능 |
|---|---|
| **↑ ↓ ← →** | 이동 |
| **Z** | 선택 / 확인 |
| **X** | 취소 |
| **M** | 메뉴 |
| **I** | 인벤토리 |
| **ESC** | 뒤로가기 |

### 난이도

| 난이도 | 적 HP | 적 공격력 | 경험치 | 드랍률 |
|--------|-------|-----------|--------|--------|
| 평온 | 70% | 60% | 120% | 130% |
| 보통 | 100% | 100% | 100% | 100% |
| 도전 | 130% | 130% | 130% | 120% |
| 악몽 | 160% | 160% | 160% | 150% |
| 지옥 | 200% | 200% | 200% | 200% |

---

## 🔧 개발 가이드

### 프로젝트 구조

```
Dawn-of-Stellar/
├── src/              # 소스 코드
│   ├── core/        # 핵심 시스템
│   ├── combat/      # 전투 시스템
│   ├── character/   # 캐릭터 시스템
│   ├── world/       # 월드/던전 생성
│   ├── ai/          # AI 시스템
│   └── ui/          # UI 시스템
├── data/            # 게임 데이터 (YAML)
├── assets/          # 에셋 (오디오, 폰트)
├── tests/           # 테스트
├── docs/            # 문서
├── web/             # 웹 버전
└── main.py          # 엔트리 포인트
```

### 테스트 실행

```bash
# 전체 테스트
pytest tests/ -v

# 커버리지 포함
pytest tests/ --cov=src --cov-report=html

# 특정 테스트만
pytest tests/unit/combat/test_damage.py -v
```

### 코드 품질 검사

```bash
# Black (포맷팅)
black src/ tests/

# isort (import 정렬)
isort src/ tests/

# Pylint (코드 품질)
pylint src/

# MyPy (타입 체킹)
mypy src/
```

### 실행 파일 빌드

게임을 실행 파일로 만들어 배포할 수 있습니다:

#### Windows

```bash
# 빌드 스크립트 실행
build_executable.bat

# 또는 수동 빌드
pip install pyinstaller
python -m PyInstaller build.spec --clean --noconfirm
```

빌드 완료 후 `dist` 폴더에 `DawnOfStellar.exe`가 생성됩니다.

#### 빌드 옵션

`build.spec` 파일을 수정하여 빌드 옵션을 변경할 수 있습니다:
- 콘솔 창 숨기기: `console=False`
- 아이콘 추가: `icon="경로/아이콘.ico"`
- UPX 압축 비활성화: `upx=False`

자세한 내용은 [배포 가이드](DEPLOYMENT_README.md)를 참조하세요.

### 빌드

```bash
# PyInstaller로 실행 파일 생성
pyinstaller DawnOfStellar.spec

# 결과물: dist/DawnOfStellar.exe (또는 DawnOfStellar)
```

---

## 🤝 기여하기

기여를 환영합니다! 다음 방법으로 참여하실 수 있습니다:

### 버그 리포트
[Issues](https://github.com/APTOL-7177/Dawn-of-Stellar/issues)에서 버그를 제보해주세요.

### 기능 제안
새로운 기능이나 개선 사항을 제안해주세요.

### Pull Request
1. Fork 프로젝트
2. Feature 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 Push (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

### 개발 가이드라인
- PEP 8 준수
- Type hints 사용
- Docstring (Google 스타일)
- 테스트 작성
- 한국어 주석 권장

자세한 내용은 [.claude/CLAUDE.md](.claude/CLAUDE.md)를 참조하세요.

---

## 📚 문서

- **[공식 Wiki](https://github.com/APTOL-7177/Dawn-of-Stellar/wiki)** - 완벽한 게임 가이드
- **[전투 시스템](https://github.com/APTOL-7177/Dawn-of-Stellar/wiki/Combat-System)** - ATB + BRV 메커니즘
- **[직업 가이드](https://github.com/APTOL-7177/Dawn-of-Stellar/wiki/Characters)** - 33개 직업 완전 분석
- **[요리 시스템](https://github.com/APTOL-7177/Dawn-of-Stellar/wiki/Cooking)** - 52개 레시피
- **[아키텍처](https://github.com/APTOL-7177/Dawn-of-Stellar/wiki/Architecture)** - 시스템 설계

---

## 🏆 게임 스탯

| 항목 | 수량 |
|------|------|
| **직업** | 33개 |
| **스킬** | 195개+ |
| **레시피** | 52개 |
| **상태 효과** | 165개 |
| **던전 레벨** | 무한 |

---

## 🎨 스크린샷

_준비 중..._

---

## 💻 시스템 요구사항

### 최소 사양
- **OS**: Windows 10, Linux (Ubuntu 20.04+), macOS 10.15+
- **Python**: 3.10 이상
- **RAM**: 512MB
- **저장공간**: 200MB

### 권장 사양
- **RAM**: 1GB 이상
- **해상도**: 1280x720 이상

---

## 📝 버전 히스토리

### v6.0.0 (2025-11-21)
- 🎉 멀티플레이 시스템 완성
- ✨ 플레이어 간 위치 실시간 동기화
- ⚔️ 멀티플레이 전투 시스템 개선
- 🎮 불릿타임 시스템 구현
- 📝 버전 6.0.0으로 업데이트

### v5.1.0 (2025-11-16)
- ✅ GitHub Actions 자동 빌드 추가
- ✅ Windows/Linux/macOS 동시 빌드
- ✅ GitHub Pages 웹사이트 배포
- ✅ Wiki 문서 정리
- ✅ CI/CD 파이프라인 구축

### v5.0.0 (2025-11-15)
- 🎉 프로젝트 재구조화
- ✨ 33개 직업 시스템 구현
- ⚔️ ATB + BRV 전투 시스템
- 🍳 52개 요리 레시피
- 🏰 절차적 던전 생성

자세한 변경사항은 [CHANGELOG.md](CHANGELOG.md)를 참조하세요.

---

## 📞 연락처 및 지원

- **GitHub Issues**: [버그 리포트 및 기능 제안](https://github.com/APTOL-7177/Dawn-of-Stellar/issues)
- **GitHub Discussions**: [커뮤니티 토론](https://github.com/APTOL-7177/Dawn-of-Stellar/discussions)
- **Wiki**: [공식 문서](https://github.com/APTOL-7177/Dawn-of-Stellar/wiki)

---

## 📜 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

## 🙏 감사의 말

- **python-tcod**: 로그라이크 개발 프레임워크
- **Dissidia Final Fantasy**: BRV 시스템 영감
- **Don't Starve**: 요리/제작 시스템 영감

---

## 🌟 스타 히스토리

[![Star History Chart](https://api.star-history.com/svg?repos=APTOL-7177/Dawn-of-Stellar&type=Date)](https://star-history.com/#APTOL-7177/Dawn-of-Stellar&Date)

---

<div align="center">

**즐거운 모험 되세요! May the stars guide you! ⭐**

[⬆ 맨 위로](#-dawn-of-stellar-별빛의-여명)

</div>
