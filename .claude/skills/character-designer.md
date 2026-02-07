# Character Designer Skill

캐릭터/직업 설계 및 밸런싱 전문 스킬

## 역할군(Archetype) 분류

| 역할 | 예시 직업 | 특징 |
|------|-----------|------|
| 물리 딜러 | 전사, 버서커, 검투사 | 높은 physical_attack, HP |
| 마법 딜러 | 흑마법사, 대마법사 | 높은 magic_attack, MP |
| 원거리 딜러 | 궁수, 건슬링어 | 높은 speed, accuracy |
| 탱커 | 기사, 팔라딘 | 높은 HP, defense |
| 힐러 | 프리스트, 음유시인 | 높은 spirit, MP |
| 디버퍼 | 도적, 닌자 | 높은 speed, luck |
| 하이브리드 | 배틀메이지, 레드메이지 | 균형 잡힌 스탯 |

## 스탯 범위 기준 (base_stats)

| 스탯 | 최소 | 중간 | 최대 | 비고 |
|------|------|------|------|------|
| hp | 140 | 170 | 210 | 탱커 높음 |
| mp | 20 | 40 | 65 | 마법사 높음 |
| init_brv | 90 | 130 | 170 | |
| physical_attack | 30 | 60 | 85 | 물리 딜러 높음 |
| physical_defense | 35 | 50 | 70 | 탱커 높음 |
| magic_attack | 25 | 55 | 90 | 마법사 높음 |
| magic_defense | 35 | 48 | 65 | |
| speed | 50 | 65 | 80 | 도적/닌자 높음 |
| max_brv | 270 | 340 | 420 | |

## 기믹(Gimmick) 설계 원칙
1. **고유성**: 각 직업의 기믹 타입은 유일해야 한다
2. **시각적 피드백**: 게이지나 상태로 현재 상황을 알 수 있어야 한다
3. **리스크-리워드**: 조건 충족 시 보상, 실패 시 페널티
4. **플레이 스타일**: 기믹이 해당 직업의 전투 방식을 유도해야 한다

### 기믹 타입 예시
- `crowd_cheer` (검투사): 관중 요구 충족 → 환호 게이지 상승
- `support_fire` (궁수): 아군 마킹 → 자동 지원 사격
- `rune_signal` (배틀메이지): 룬 부여 → 폭발 데미지
- `yomi` (사무라이): 적 행동 예측 → 선제/반격
- `duty` (기사): 의무 이행 → 팀 버프
- `faith` (프리스트): 신앙 축적 → 기적 발동

## 트레이트(Trait) 설계
```yaml
traits:
  - id: <unique_snake_case>
    name: <한글 이름>
    description: <설명>
    type: passive|conditional
    conditions:             # conditional일 때만
      <condition_key>: <value>
    effects:
      <effect_key>: <value>
```

### 패시브 vs 조건부
- **passive**: 항상 적용 (예: 명중률 +10%)
- **conditional**: 특정 조건 충족 시 적용 (예: HP 30% 이하 시 공격력 +50%)

## 새 직업 체크리스트
- [ ] 역할군 결정 (Archetype)
- [ ] base_stats 설계 (기존 범위 내)
- [ ] stat_growth 설계
- [ ] 기믹 설계 (고유 타입)
- [ ] 트레이트 4~5개 설계
- [ ] 스킬 6~8개 설계
- [ ] YAML 파일 생성
- [ ] 기믹 로직 구현
- [ ] 트레이트 효과 구현
- [ ] 테스트
