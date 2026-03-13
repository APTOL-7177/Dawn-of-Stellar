<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# docs/wiki/

## Purpose
게임 위키 페이지. 게임 시스템, 메커니즘, 플레이 가이드를 설명합니다. 플레이어 및 개발자용 참고 자료입니다.

## Key Files
| File | Description |
|------|-------------|
| skill_system_guide.md | 스킬 시스템 설명 |
| job_system_guide.md | 직업 시스템 설명 |
| combat_system_guide.md | 전투 시스템 (ATB, 데미지 계산) |
| gimmick_system_guide.md | 직업 고유 메커니즘 설명 |
| teamwork_system_guide.md | 팀워크 스킬 시스템 |
| cooking_guide.md | 요리/합성 시스템 |
| multiplayer_guide.md | 멀티플레이어 가이드 |
| world_exploration_guide.md | 월드 탐사 가이드 |

## Structure Per File
```markdown
# 시스템명

## 개요
시스템 목적 설명

## 기본 개념
- 개념 1
- 개념 2

## 플레이어 가이드
단계별 사용 방법

## 예시
구체적 예시

## 팁 & 전략
고급 플레이 팁
```

## For AI Agents

### Working In This Directory
- 위키 페이지는 시스템 설명서
- data/ 및 src/ 의 기능을 플레이어 관점에서 설명
- 새 기능 추가 시 wiki 문서도 함께 업데이트

### Common Patterns
- 목차 기반 구조 (Overview -> Basics -> Advanced)
- 예시 코드 또는 게임플레이 이미지
- 참고 링크 (관련 시스템으로)

## Dependencies
- 위키는 참고 자료 (런타임 의존성 없음)
- src/ui/ - 게임 내 헬프 텍스트와 일치

<!-- MANUAL: -->
