# YAML Skill Expert

YAML 기반 스킬 시스템의 생성, 검증, 디버깅 전문 스킬

## 스킬 데이터 구조

### 기본 스킬 템플릿
```yaml
id: <snake_case>          # 파일명과 일치
name: <한글 스킬명>
type: <스킬 타입>
description: <한글 설명>
costs:
  mp: <정수>
  cast_time: <float, 보통 0.8~2.0>
effects:
  - type: damage
    element: <속성>
    multiplier: <float>
    stat_base: <strength|magic>
sfx:
  - se
  - <효과음명>
```

### 스킬 타입
- `brv_attack`: BRV 공격 (기본)
- `hp_attack`: HP 직접 공격
- `brv_hp_attack`: BRV → HP 복합 공격
- `support`: 지원/버프
- `debuff`: 디버프
- `ultimate`: 궁극기
- `toggle`: 토글 (켜기/끄기)

### 이펙트 타입
```yaml
# 데미지
- type: damage
  element: physical|fire|ice|thunder|holy|dark|wind|earth|water|non_elemental
  multiplier: <float>
  stat_base: strength|magic
  hits: <int, 다단히트>
  ignore_defense: <0~1, 방어 관통 비율>

# 상태이상
- type: status
  effect: <poison|blind|slow|stun|burn|...>
  duration: <턴 수>
  chance: <0~1>

# 회복
- type: heal
  stat_base: magic
  multiplier: <float>

# 버프
- type: buff
  stat: <physical_attack|speed|...>
  multiplier: <float>
  duration: <턴 수>

# BRV 회복
- type: brv_recovery
  amount: <정수 또는 비율>
```

### 확장 필드
```yaml
# 조건부 효과
conditions:
  hp_below: 0.3          # HP 30% 이하일 때
  has_status: "poison"    # 특정 상태이상일 때

# 쿨다운
cooldown: <턴 수>

# 범위
target: single|all|random|self|ally|all_allies

# 커스텀 핸들러 연결
custom_handler: <handler_function_name>

# 토글 스킬
toggle_mp_per_turn: <유지 MP>
```

## 로딩 경로
1. `src/character/skills/yaml_skill_loader.py` → YAML 파일 파싱
2. `src/character/skills/skill_manager.py` → 스킬 등록/관리
3. `src/character/skills/skill_initializer.py` → 초기화 시 전체 로드
4. `src/character/skills/custom_handlers.py` → 특수 효과 핸들러
5. `src/character/skills/effects/` → 효과별 처리기

## 밸런스 기준
| 등급 | MP | 배율 | cast_time |
|------|-----|------|-----------|
| 기본 | 15~25 | 1.5~2.5x | 0.8~1.2 |
| 중급 | 25~40 | 2.5~4.0x | 1.0~1.5 |
| 강력 | 40~60 | 4.0~6.0x | 1.5~2.0 |
| 궁극기 | 60~100 | 6.0~10.0x | 2.0~3.0 |

## 검증 체크리스트
- [ ] `id`가 파일명과 일치하는가
- [ ] `name`, `type`, `costs` 필드 존재
- [ ] `effects` 리스트가 비어있지 않은가
- [ ] `multiplier` 값이 밸런스 범위 내인가
- [ ] 해당 스킬이 캐릭터 YAML의 `skills:` 에 포함되어 있는가
- [ ] 커스텀 핸들러가 필요한 경우 등록되어 있는가
