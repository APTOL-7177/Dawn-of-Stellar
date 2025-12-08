# YAML 스킬 SFX 가이드

## 개요

모든 YAML 기반 스킬 파일에 적절한 SFX(효과음)를 자동으로 추가했습니다.
총 **405개** 스킬 파일 중 **399개**에 새로운 SFX가 추가되었습니다.

## 적용 일자

- 2025-12-04

## SFX 매핑 규칙

### 직업별 매핑

각 직업은 고유한 SFX 매핑 규칙을 가지고 있습니다:

#### 해커 (Hacker)
- **기본**: Computer
- **특수**:
  - DDOS 공격: Laser1
  - 바이러스: Poison
  - 방화벽: Barrier
  - 루트킷: Darkness3
  - 제로데이: Explosion2
  - 궁극기: Explosion4

#### 정령술사 (Elementalist)
- **기본**: Magic1
- **특수**:
  - 불 속성: Fire2
  - 얼음 속성: Ice2
  - 번개 속성: Thunder2
  - 대지 속성: Earth1
  - 바람 속성: Wind1
  - 물 속성: Water1
  - 융합 스킬: Magic2
  - 오버로드: Explosion3
  - 궁극기: Explosion4
  - 팀워크: Summon

#### 샤먼 (Shaman)
- **기본**: Magic1
- **특수**:
  - 영혼 스킬: Magic2
  - 저주/역병: Poison
  - 악몽: Darkness3
  - 정화: Heal4
  - 축복: Up1
  - 궁극기: Explosion4
  - 팀워크: Summon

#### 팔라딘 (Paladin)
- **기본**: Sword2
- **특수**:
  - 성스러운 스킬: Heal4
  - 강타: Damage5
  - 해머: Blow10
  - 심판: Thunder2
  - 방패/보호: Barrier
  - 축복: Up1
  - 분노: Fire2
  - 궁극기: Explosion4
  - 팀워크: Summon

#### 나이트 (Knight)
- **기본**: Sword2
- **특수**:
  - 강타: Blow10
  - 창: Damage3
  - 방패: Barrier
  - 맹세/충성: Up1
  - 궁극기: Explosion4
  - 팀워크: Summon

#### 글래디에이터 (Gladiator)
- **기본**: Sword2
- **특수**:
  - 경기장 스킬: Damage3
  - 함성: Blow10
  - 영광 스킬: Damage5
  - 명예 스킬: Sword4
  - 챔피언 스킬: Up2
  - 화려한 스킬: Explosion2
  - 궁극기: Explosion4
  - 팀워크: Summon

#### 로그 (Rogue)
- **기본**: Slash1
- **특수**:
  - 그림자 스킬: Darkness3
  - 백스탭: Damage5
  - 독: Poison
  - 연막: Blind
  - 도둑질: Item1
  - 궁극기: Explosion4
  - 팀워크: Summon

#### 워리어 (Warrior)
- **기본**: Sword2
- **특수**:
  - 타격: Damage3
  - 보루: Barrier
  - 수호: Up1
  - 궁극기: Explosion4
  - 팀워크: Summon

#### 차원술사 (Dimensionist)
- **기본**: Magic1
- **특수**:
  - 차원 스킬: Move2
  - 굴절: Reflection
  - 장벽: Barrier
  - 폭발: Explosion2
  - 산란: Wind1
  - 시간 스킬: Up2
  - 궁극기: Explosion4
  - 팀워크: Summon

#### 프리스트 (Priest)
- **기본**: Heal1
- **특수**:
  - 힐: Recovery
  - 축복: Up1
  - 강타: Thunder1
  - 심판: Thunder2
  - 기적: Heal4
  - 부활: Raise1
  - 은총: Up2
  - 궁극기: Explosion4
  - 팀워크: Summon

### 일반 스킬 타입별 매핑

직업별 매핑이 없는 경우, 스킬 타입에 따라 자동으로 매핑됩니다:

#### 공격 스킬
- 물리 공격: Damage3
- 베기: Slash1
- 강타: Damage3
- 찌르기: Slash2
- 마법 공격: Magic1

#### 속성 마법
- 불: Fire1
- 얼음: Ice1
- 번개: Thunder1
- 대지: Earth1
- 바람: Wind1
- 물: Water1
- 어둠: Darkness3
- 성: Heal4

#### 지원 스킬
- 힐: Recovery
- 버프: Up1
- 보호막: Barrier
- 디버프: Down1
- 독: Poison
- 저주: Darkness3

#### 특수 스킬
- 궁극기: Explosion4
- 팀워크: Summon
- 소환: Summon

## 사용 방법

### 스크립트 실행

```bash
# 모든 스킬에 SFX 추가
python scripts/add_sfx_to_skills.py

# 미리보기 (파일 변경 없이)
python scripts/add_sfx_to_skills.py --dry-run

# 특정 직업만 처리
python scripts/add_sfx_to_skills.py --filter hacker
```

### 새 스킬에 SFX 추가

새로운 YAML 스킬을 만들 때는 다음과 같이 SFX를 추가하세요:

```yaml
id: my_skill
name: 내 스킬
type: attack
description: 스킬 설명
target: enemy
effects:
  - type: damage
    damage_type: brv
    multiplier: 2.0
sfx:
  - se
  - Damage3  # 적절한 효과음 이름
```

### 사용 가능한 SFX 목록

`config.yaml` 파일의 `audio.sfx` 섹션에서 모든 사용 가능한 SFX를 확인할 수 있습니다.

주요 카테고리:
- `combat`: 전투 효과음
- `skill`: 스킬 효과음
- `character`: 캐릭터 효과음
- `item`: 아이템 효과음
- `ui`: UI 효과음
- `world`: 월드 효과음

## 테스트

```bash
# SFX 로딩 테스트
python -m pytest tests/test_yaml_skill_sfx.py -v

# 게임 실행 테스트
python main.py --dev
```

## 파일 구조

```
data/skills/
├── hacker_basic_breach.yaml      # SFX: [se, Computer]
├── paladin_holy_smite.yaml       # SFX: [se, Heal4]
├── shaman_spirit_arrow.yaml      # SFX: [se, Magic2]
├── elementalist_teamwork.yaml    # SFX: [se, Summon]
└── ... (405개 파일)
```

## 문제 해결

### SFX가 재생되지 않는 경우

1. `config.yaml`에서 `audio.sfx.enabled: true` 확인
2. `audio.sfx_volume` 확인 (0.0 ~ 1.0)
3. 올바른 SFX 이름 사용 확인 (`config.yaml` 참조)
4. 오디오 파일 존재 확인: `assets/audio/se/`

### SFX 이름 변경하기

YAML 파일에서 직접 수정:

```yaml
sfx:
  - se
  - NewSoundEffect  # 원하는 효과음으로 변경
```

또는 스크립트를 수정하여 재실행:

```python
# scripts/add_sfx_to_skills.py
SFX_MAPPING["your_job"]["keywords"]["your_keyword"] = ("se", "YourSFX")
```

## 통계

- **총 스킬 파일**: 405개
- **새로 SFX 추가**: 399개
- **이미 SFX 존재**: 6개
- **처리 오류**: 0개

## 향후 작업

- [ ] 각 스킬의 SFX 피치(Pitch) 조정 시스템 추가
- [ ] 스킬 체인 시 SFX 믹싱 시스템
- [ ] 3D 위치 기반 SFX (스테레오 패닝)
- [ ] 스킬별 커스텀 SFX 오버라이드 시스템

---

**작성일**: 2025-12-04
**작성자**: Claude Code
**버전**: 1.0
