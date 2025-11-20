# Dawn of Stellar (별빛의 여명) - 공식 Wiki

<div align="center">

![Dawn of Stellar Banner](https://img.shields.io/badge/Dawn%20of%20Stellar-6.0.0-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-green?style=for-the-badge&logo=python)
![Genre](https://img.shields.io/badge/Genre-Roguelike%20RPG-red?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**Final Fantasy 스타일의 ATB + BRV 전투 시스템을 가진 로그라이크 RPG**

[시작하기](Getting-Started.md) | [전투 시스템](../combat-system.md) | [직업 가이드](Character-Classes-Complete-Guide.md) | [GitHub](https://github.com/APTOL-7176/Dos)

</div>

---

## 🌟 게임 소개

**Dawn of Stellar**는 Final Fantasy의 ATB(Active Time Battle) 시스템과 Dissidia의 BRV(Brave) 시스템을 독창적으로 결합한 로그라이크 RPG입니다. 매번 새롭게 생성되는 던전에서 33개의 독특한 직업, 195개 이상의 스킬, 그리고 전략적인 전투를 경험하세요!

### ✨ 핵심 특징

| 특징 | 설명 |
|------|------|
| 🎭 **33개 고유 직업** | 각 직업마다 독자적인 기믹 시스템 (스탠스, 검기, 룬, 시간 조작 등) |
| ⚔️ **ATB + BRV 전투** | 실시간 액션과 전략의 완벽한 조화 |
| 📜 **195+ 스킬** | BRV 공격, HP 공격, 궁극기, 지원/디버프 스킬 |
| 🏰 **절차적 던전** | BSP 알고리즘으로 매번 다른 던전 생성 |
| ⭐ **메타 진행** | 별조각으로 새로운 직업과 패시브 스킬 해금 |
| 🍳 **요리 & 제작** | Don't Starve 스타일의 52개 레시피 |
| 🌍 **완전 한국어** | 모든 UI, 텍스트, 튜토리얼 한국어 지원 |
| 🌐 **멀티플레이어** | 최대 4인 협동 멀티플레이 |

---

## 📚 Wiki 목차

### 🎮 플레이어 가이드

<table>
<tr>
<td width="50%">

#### 기초 가이드
- **[시작 가이드](Getting-Started.md)** - 게임 설치부터 첫 던전까지
- **[전투 시스템](../combat-system.md)** - ATB, BRV, 데미지 계산
- **[직업 완벽 가이드](Character-Classes-Complete-Guide.md)** - 33개 직업 상세 분석
- **[스킬 데이터베이스](Skills-Database.md)** - 195개 스킬 완전 정복
- **[요리 시스템](../cooking.md)** - 52개 레시피 가이드

</td>
<td width="50%">

#### 고급 전략
- **[고급 전투 전략](Advanced-Combat-Strategies.md)** - 프로의 전투 기술
- **[보스 공략](Boss-Strategies.md)** - 보스별 패턴과 공략법
- **[패시브 스킬 가이드](Passive-Skills-Guide.md)** - 최적 패시브 빌드
- **[장비 시스템](Equipment-System.md)** - 장비 등급, 효과, 세팅
- **[월드 & 던전](World-and-Dungeons.md)** - 탐험과 던전 공략

</td>
</tr>
</table>

### 🔧 시스템 가이드

- **[메타 진행 시스템](Meta-Progression.md)** - 별조각, 직업 해금, 업그레이드
- **[팁과 요령](Tips-and-Tricks.md)** - 숨겨진 팁과 효율적인 플레이
- **[FAQ](FAQ.md)** - 자주 묻는 질문과 답변

### 🛠️ 개발자 문서

- **[프로젝트 구조](../architecture.md)** - 시스템 아키텍처
- **[기여 가이드](../../CONTRIBUTING.md)** - 프로젝트 기여 방법
- **[개발자 가이드](../../.claude/CLAUDE.md)** - 개발 환경 설정

---

## 🎯 빠른 시작

### 설치 방법

```bash
# 1. 저장소 클론
git clone https://github.com/APTOL-7176/Dos.git
cd Dos

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 게임 실행
python main.py
```

### 첫 게임을 위한 팁

1. **초보자 추천 직업**: 전사, 성직자, 궁수
2. **난이도**: 처음에는 "평온" 난이도 추천
3. **전투 기본**: BRV 공격으로 축적 → HP 공격으로 데미지
4. **BREAK 시스템**: 적 BRV를 0으로 만들면 보너스 데미지!

자세한 내용은 **[시작 가이드](Getting-Started.md)**를 참고하세요!

---

## ⚔️ 전투 시스템 미리보기

```
[전투 흐름]
ATB 게이지 충전 (0 → 1000)
    ↓
행동 선택 (BRV 공격 / HP 공격 / 스킬)
    ↓
BRV 축적 (적 BRV 깎기 + 내 BRV 쌓기)
    ↓
BREAK 발동? (적 BRV = 0)
    ↓
HP 공격 (축적된 BRV로 실제 HP 데미지)
    ↓
승리 / 패배 판정
```

### ATB (Active Time Battle)
- **게이지**: 0~2000 (행동 임계값 1000)
- **증가율**: 속도 스탯에 비례
- **실시간**: 적도 동시에 ATB 증가

### BRV (Brave) 시스템
- **BRV 공격**: HP 데미지 없이 BRV만 축적
- **HP 공격**: 축적된 BRV를 소비하여 HP 데미지
- **BREAK**: 적 BRV를 0으로 만들면 보너스 +50% 데미지

→ **[전투 시스템 완벽 가이드](../combat-system.md)** 에서 더 알아보기

---

## 🎭 직업 시스템

### 6가지 아키타입

| 아키타입 | 대표 직업 | 특징 |
|---------|----------|------|
| 💪 **물리 딜러** | 전사, 검성, 광전사 | 높은 물리 공격력, BREAK 특화 |
| ✨ **마법 딜러** | 아크메이지, 정령술사 | 속성 마법, 광역 공격 |
| 🛡️ **탱커** | 기사, 성기사 | 높은 방어력, 파티 보호 |
| ❤️ **힐러/서포터** | 성직자, 신관, 바드 | 회복, 버프, 파티 지원 |
| 🗡️ **암살/은신** | 암살자, 도적 | 크리티컬, 은신, 회피 |
| 🔮 **특수** | 시간술사, 차원술사, 철학자 | 시간 조작, 확률 조작, 특수 기믹 |

→ **[직업 완벽 가이드](Character-Classes-Complete-Guide.md)** 에서 33개 직업 상세 정보 확인

---

## 🏆 난이도 시스템

| 난이도 | 적 HP | 적 공격력 | 경험치 | 드랍률 | 추천 대상 |
|--------|-------|-----------|--------|--------|----------|
| 평온 | 70% | 60% | 120% | 130% | 초보자 |
| 보통 | 100% | 100% | 100% | 100% | 일반 플레이어 |
| 도전 | 130% | 130% | 130% | 120% | 숙련자 |
| 악몽 | 160% | 160% | 160% | 150% | 전문가 |
| 지옥 | 200% | 200% | 200% | 200% | 하드코어 |

---

## 🍳 요리 시스템

52개의 레시피로 전투를 준비하세요!

### 요리 카테고리
- 🇰🇷 **한식** (11개): 김치찌개, 비빔밥, 삼계탕, 불고기...
- 🇯🇵 **일식** (9개): 초밥, 라멘, 튀김, 사시미...
- 🍝 **양식** (9개): 스테이크, 파스타, 피자...
- 🥘 **중식** (7개): 마파두부, 탕수육, 짜장면...
- 🍰 **디저트** (7개): 사과 파이, 치즈케이크...
- ☕ **음료** (4개): 허브차, 마나 커피...
- ⭐ **특수** (5개): 드래곤 바비큐, 불로장생 복숭아...

→ **[요리 시스템 완벽 가이드](../cooking.md)** 에서 더 알아보기

---

## 📊 게임 통계

<table>
<tr>
<td align="center"><b>33</b><br>직업</td>
<td align="center"><b>195+</b><br>스킬</td>
<td align="center"><b>52</b><br>레시피</td>
<td align="center"><b>50+</b><br>패시브</td>
</tr>
<tr>
<td align="center"><b>무한</b><br>던전 층수</td>
<td align="center"><b>5</b><br>난이도</td>
<td align="center"><b>100+</b><br>장비</td>
<td align="center"><b>30+</b><br>적 종류</td>
</tr>
</table>

---

---

## 🔗 유용한 링크

### 공식 링크
- 🌐 **[GitHub 저장소](https://github.com/APTOL-7176/Dos)**
- 🐛 **[버그 리포트](https://github.com/APTOL-7176/Dos/issues)**
- 📝 **[개발 로드맵](https://github.com/APTOL-7176/Dos/projects)**
- 💬 **[토론 포럼](https://github.com/APTOL-7176/Dos/discussions)**

### 커뮤니티
- 💡 **팁 공유** - [Tips-and-Tricks.md](Tips-and-Tricks.md)
- 🤔 **질문** - [FAQ.md](FAQ.md)
- 🏆 **고급 전략** - [Advanced-Combat-Strategies.md](Advanced-Combat-Strategies.md)

---

## 🎮 시스템 요구사항

| 최소 사양 | 권장 사양 |
|-----------|-----------|
| **OS**: Windows 10, Linux, macOS | **OS**: Windows 11, Linux, macOS |
| **Python**: 3.10+ | **Python**: 3.11+ |
| **RAM**: 512MB | **RAM**: 1GB |
| **저장공간**: 200MB | **저장공간**: 500MB |
| **해상도**: 800×600 | **해상도**: 1920×1080 |

---

## 📜 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능합니다.

---

## 🙏 기여자

이 프로젝트에 기여해주신 모든 분들께 감사드립니다!

버그 리포트, 기능 제안, 코드 기여 모두 환영합니다!
- **이슈 제출**: [GitHub Issues](https://github.com/APTOL-7176/Dos/issues)
- **기여 가이드**: [CONTRIBUTING.md](../../CONTRIBUTING.md)

---

## 🌟 최신 업데이트

### 버전 6.0.0 (2025-01-XX)
- 🎉 멀티플레이 시스템 완성
- ✨ 플레이어 간 위치 실시간 동기화
- ⚔️ 멀티플레이 전투 시스템 개선
- 🎮 불릿타임 시스템 구현
- 📝 버전 6.0.0으로 업데이트

### 버전 5.0.0 (2025-11-15)
- ✅ 33개 직업 시스템 완성
- ✅ 195개 스킬 구현
- ✅ 52개 요리 레시피 추가
- ✅ 메타 진행 시스템 구현
- ✅ 패시브 스킬 시스템 완성

---

<div align="center">

## 🌠 별빛의 여명에 오신 것을 환영합니다!

**May the stars guide you on your journey! ⭐**

[시작하기](Getting-Started.md) | [전투 가이드](../combat-system.md) | [직업 가이드](Character-Classes-Complete-Guide.md)

---

*이 Wiki는 지속적으로 업데이트됩니다. 마지막 업데이트: 2025-11-16*

</div>
