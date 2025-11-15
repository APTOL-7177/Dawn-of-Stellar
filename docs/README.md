# Dawn of Stellar (별빛의 여명) - 공식 위키

> Final Fantasy 스타일의 ATB + BRV 전투 시스템을 가진 로그라이크 RPG

![Version](https://img.shields.io/badge/version-5.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

---

## 📖 목차

1. [게임 소개](#게임-소개)
2. [빠른 시작](#빠른-시작)
3. [핵심 시스템](#핵심-시스템)
4. [위키 목록](#위키-목록)
5. [개발팀](#개발팀)

---

## 🎮 게임 소개

**Dawn of Stellar**는 Final Fantasy의 ATB 전투 시스템과 Dissidia의 BRV 시스템을 결합한 독창적인 로그라이크 RPG입니다.

### 핵심 특징

- **33개의 고유한 직업** - 각각 독자적인 기믹 시스템 보유
- **ATB + BRV 전투** - 실시간 액션과 전략의 완벽한 조화
- **195개 이상의 스킬** - 다채로운 전투 경험
- **절차적 던전 생성** - 매번 다른 도전
- **메타 진행 시스템** - 별조각으로 새로운 직업 해금
- **요리 & 제작 시스템** - Don't Starve 스타일의 서바이벌 요소
- **Final Fantasy VII OST** - 오리지널 BGM과 효과음

### 장르

로그라이크 RPG + JRPG 퓨전

### 플랫폼

Windows, Linux, macOS (Python 3.10+)

---

## 🚀 빠른 시작

### 설치 및 실행

```bash
# 저장소 클론
git clone https://github.com/APTOL-7176/Dos.git
cd Dos

# 의존성 설치
pip install -r requirements.txt

# 게임 실행
python main.py

# 개발 모드 (모든 직업 해금)
python main.py --dev

# 디버그 모드
python main.py --debug --log=DEBUG
```

### 시스템 요구사항

- **Python**: 3.10 이상
- **RAM**: 최소 512MB
- **저장공간**: 200MB
- **OS**: Windows 10/11, Linux, macOS

---

## ⚔️ 핵심 시스템

### 1. ATB (Active Time Battle)

- **게이지**: 0~2000
- **행동 임계값**: 1000
- **증가율**: 캐릭터 속도에 비례
- **실시간 전투**: 적도 동시에 ATB 증가

### 2. BRV (Brave) 시스템

```
BRV 공격 → BRV 축적 → HP 공격 → 실제 데미지
```

- **BRV 공격**: HP 데미지 없이 BRV만 축적
- **HP 공격**: 축적된 BRV를 소비하여 HP 데미지
- **BREAK**: 적 BRV를 0으로 만들면 보너스 데미지 + 스턴

### 3. 직업 시스템

33개 직업, 6가지 아키타입:
- 물리 딜러 (전사, 검성, 광전사 등)
- 마법 딜러 (아크메이지, 정령술사 등)
- 탱커 (기사, 성기사 등)
- 힐러/서포터 (성직자, 신관, 바드 등)
- 암살/은신 (암살자, 도적 등)
- 특수 (해커, 차원술사, 철학자 등)

### 4. 난이도 시스템

| 난이도 | 적 HP | 적 공격력 | 경험치 | 드랍률 |
|--------|-------|-----------|--------|--------|
| 평온 | 70% | 60% | 120% | 130% |
| 보통 | 100% | 100% | 100% | 100% |
| 도전 | 130% | 130% | 130% | 120% |
| 악몽 | 160% | 160% | 160% | 150% |
| 지옥 | 200% | 200% | 200% | 200% |

---

## 📚 위키 목록

### 게임 가이드

- **[전투 시스템](combat-system.md)** - ATB, BRV, 데미지 계산 완벽 가이드
- **[직업 가이드](characters/README.md)** - 33개 직업 완전 분석
- **[스킬 시스템](skills.md)** - 195개 스킬 데이터베이스
- **[장비 시스템](equipment.md)** - 장비 등급, 효과, 드랍률
- **[요리 시스템](cooking.md)** - 52개 레시피 완벽 가이드
- **[필드 시스템](field-systems.md)** - 채집, 탐험, 상호작용
- **[메타 진행](meta-progression.md)** - 별조각, 직업 해금

### 플레이어 팁

- **[초보자 가이드](guides/beginner.md)** - 처음 시작하는 분들을 위한 가이드
- **[추천 빌드](guides/builds.md)** - 직업별 추천 패시브 조합
- **[보스 공략](guides/bosses.md)** - 보스 패턴 및 공략법
- **[효율적인 파밍](guides/farming.md)** - 레벨링, 골드, 아이템 파밍

### 개발자 문서

- **[개발자 가이드](developer-guide.md)** - 프로젝트 구조 및 개발 가이드
- **[API 레퍼런스](api-reference.md)** - 코드 API 문서
- **[아키텍처](architecture.md)** - 시스템 설계 문서
- **[기여 가이드](CONTRIBUTING.md)** - 프로젝트 기여 방법

### 데이터베이스

- **[직업 데이터](database/characters.md)** - 전체 직업 스탯 및 성장률
- **[스킬 데이터](database/skills.md)** - 전체 스킬 효과 및 비용
- **[장비 데이터](database/equipment.md)** - 전체 장비 목록
- **[적 데이터](database/enemies.md)** - 적 종류 및 스탯

---

## 🎯 게임 플레이 팁

### 초보자를 위한 조언

1. **처음에는 "평온" 난이도로 시작**
   - 시스템에 익숙해질 때까지 쉬운 난이도 추천

2. **추천 초보 직업**
   - **전사**: 높은 체력과 방어력, 다양한 스탠스
   - **성직자**: 힐링으로 생존력 증가
   - **궁수**: 원거리 안전 딜링

3. **BRV 관리가 핵심**
   - BRV를 충분히 쌓은 후 HP 공격
   - BREAK를 노려 보너스 데미지 획득

4. **패시브 스킬 선택**
   - 초반: HP 증폭, 신속, 자동 재생 추천
   - 중반: 힘의 축복, 치명타 강화
   - 후반: 불사조의 가호, 이중 시전

5. **요리 활용**
   - 전투 전 요리로 버프 획득
   - 드래곤 스테이크 = 최대 HP +30

### 고급 전략

- **ATB 관리**: 속도 스탯을 올려 더 자주 행동
- **속성 약점 공략**: 적의 약점 속성 파악
- **상처 시스템 활용**: HP 데미지의 25%가 상처로 누적
- **BREAK 연계**: 여러 캐릭터가 동시에 BRV 공격 후 BREAK

---

## 👥 개발팀

### 프로젝트 정보

- **프로젝트명**: Dawn of Stellar (별빛의 여명)
- **버전**: 5.0.0
- **개발 언어**: Python 3.10+
- **게임 엔진**: TCOD (libtcod)
- **저장소**: https://github.com/APTOL-7176/Dos

### 라이선스

MIT License

### 기여

버그 리포트, 기능 제안, 코드 기여 모두 환영합니다!
- GitHub Issues: https://github.com/APTOL-7176/Dos/issues
- Pull Requests: https://github.com/APTOL-7176/Dos/pulls

---

## 🔗 관련 링크

- [GitHub 저장소](https://github.com/APTOL-7176/Dos)
- [버그 리포트](https://github.com/APTOL-7176/Dos/issues)
- [개발 로드맵](https://github.com/APTOL-7176/Dos/projects)

---

**즐거운 모험 되세요! May the stars guide you! ⭐**
