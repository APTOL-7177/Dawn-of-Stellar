# Content Generator Skill

게임 콘텐츠 자동 생성

## 목적
- 새 캐릭터 클래스 템플릿 생성
- 스킬 데이터 생성
- 아이템 생성
- 던전 테마 생성

## 사용법
```
@content-generator create-character "클래스명" [타입]
@content-generator create-skill "스킬명" [타입]
@content-generator create-item "아이템명" [등급]
```

## 생성 템플릿

### 1. 캐릭터 클래스
```yaml
class_name: "생성된_클래스"
description: "AI가 생성한 설명"
base_stats:
  hp: [밸런스된 값]
  mp: [밸런스된 값]
  strength: [역할에 맞는 값]
  # ... 자동 계산
skills:
  - [클래스에 어울리는 스킬 6개]
passives:
  - [적절한 패시브 2개]
```

### 2. 스킬
```yaml
id: generated_skill_name
name: "생성된 스킬"
type: [적절한 타입]
description: "AI가 생성한 설명"
costs:
  mp: [밸런스된 값]
  cast_time: [적절한 시간]
effects:
  - [밸런스된 효과들]
```

### 3. 아이템
```yaml
id: generated_item
name: "생성된 아이템"
type: [무기/방어구/소비품]
rarity: [희귀도]
effects:
  [능력치 보너스 등]
price: [적절한 가격]
```

## 밸런싱 규칙
- 기존 데이터와 일관성 유지
- 레벨별 적절한 파워 레벨
- 다양성과 독특함 보장
