# Add Character Command

새로운 캐릭터 클래스를 추가합니다.

## 사용법
`/add-character <class_name>`

예: `/add-character 암살자`

## 실행 내용

새 캐릭터 클래스를 추가하기 위해 다음 작업을 수행합니다:

### 1. 클래스 정의 파일 생성
`src/character/classes/<class_name>.py` 생성:
```python
from src.character.character import Character
from typing import Dict, Any

class Assassin(Character):
    """암살자 클래스"""

    BASE_STATS = {
        "hp": 90,
        "mp": 50,
        "strength": 14,
        "defense": 8,
        "magic": 10,
        "spirit": 10,
        "speed": 20,  # 매우 높은 속도
        "luck": 15
    }

    def __init__(self, name: str):
        super().__init__(name, "암살자", self.BASE_STATS)
        self.setup_skills()

    def setup_skills(self):
        # 스킬 설정
        pass
```

### 2. 데이터 파일 생성
`data/characters/<class_name>.yaml` 생성:
```yaml
class_name: "암살자"
description: "은밀함과 치명타에 특화된 클래스"
base_stats:
  hp: 90
  mp: 50
  strength: 14
  defense: 8
  magic: 10
  spirit: 10
  speed: 20
  luck: 15

skills:
  - shadow_strike
  - poison_blade
  - vanish
  - critical_eye

passives:
  - backstab_mastery
  - shadow_step

stat_growth:
  hp: 8
  mp: 4
  strength: 1.2
  speed: 1.5
```

### 3. 스킬 추가
각 스킬에 대해 `data/skills/` 에 정의 파일 생성

### 4. 클래스 등록
`src/character/classes/__init__.py` 업데이트:
```python
from .assassin import Assassin

CLASS_REGISTRY = {
    # ... 기존 클래스들
    "암살자": Assassin,
}
```

### 5. 테스트 작성
`tests/unit/character/test_<class_name>.py` 생성

### 6. 문서 업데이트
- `docs/guides/characters.md` 에 클래스 정보 추가
- 스킬 설명 추가

## 체크리스트
- [ ] 클래스 파일 생성
- [ ] 데이터 파일 생성
- [ ] 스킬 정의
- [ ] 클래스 등록
- [ ] 테스트 작성
- [ ] 문서 업데이트
- [ ] 테스트 실행 확인
