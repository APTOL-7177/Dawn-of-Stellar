<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# data/story_mode/

## Purpose
스토리 모드 설정 및 챕터 정의. 게임의 스토리 진행, 보스 전투, 튜토리얼 통합을 관리합니다.

## Key Files
| File | Description |
|------|-------------|
| (none at root) | chapters/ 하위디렉토리에 모든 챕터 정의 |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| chapters/ | 스토리 챕터 YAML 파일 (chapter_1.yaml, chapter_2.yaml 등) |

## For AI Agents

### Working In This Directory
- 스토리 모드는 chapters/ 에 계층적으로 정의됨
- src/story_mode/ 모듈에서 스토리 진행 관리

### Common Patterns
- 각 챕터: 보스 전투, 대사(dialogue), 보상, 다음 챕터 링크

## Dependencies
- src/story_mode/ - 스토리 런타임
- data/story_mode/chapters/ - 챕터 정의

<!-- MANUAL: -->
