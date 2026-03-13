<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# docs/design/

## Purpose
직업별 리메이크 설계 문서. 14개 직업의 리디자인, 메커니즘 개선, 밸런스 조정 내역을 기록합니다.

## Key Files
| File | Description |
|------|-------------|
| warrior_rework.md | 전사 직업 리메이크 |
| berserker_rework.md | 광전사 리메이크 |
| knight_rework.md | 기사 리메이크 |
| rogue_rework.md | 로그 리메이크 |
| mage_rework.md | 마법사 리메이크 |
| (10개 더) | 다른 직업 리메이크 (총 14개) |

## Structure Per File
```markdown
# 직업명 리메이크

## 개요
- 기존 문제점
- 개선 목표
- 메커니즘 변경

## 스탯 변경
- HP: 100 -> 110 (+10%)
- ATK: 18 -> 20 (+11%)

## 스킬 변경
- 신규 추가: skill_name (설명)
- 제거: old_skill
- 수정: modified_skill (변경 내역)

## 밸런스 영향도
- 강점: 설명
- 약점: 설명
```

## For AI Agents

### Working In This Directory
- 각 문서는 직업별 설계 변경 이력 기록
- data/characters/ YAML 수정의 근거 문서
- design review 및 밸런스 논의 참고 자료

### Common Patterns
- 개요: 문제점 -> 목표 -> 해결안
- 스탯: 변경 전후 비교
- 스킬: 신규/제거/수정 분류
- 영향도: 상대 직업과의 밸런스

## Dependencies
- data/characters/*.yaml - 실제 구현
- 설계 문서는 참고용 (런타임 의존성 없음)

<!-- MANUAL: -->
