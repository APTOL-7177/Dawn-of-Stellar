<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# data/story_mode/chapters/

## Purpose
스토리 챕터별 정의. 각 챕터는 보스 전투, 대사, 보상, 진행 조건을 포함합니다.

## Key Files
| File | Description |
|------|-------------|
| chapter_1.yaml | 1번 챕터 (보스, 대사, 보상) |
| chapter_2.yaml | 2번 챕터 |
| chapter_N.yaml | N번 챕터 |

## Structure Per File
```yaml
chapter_id: "chapter_1"
title: "여정의 시작"
description: "처음 만나는 보스와의 전투"
boss:
  name: "Forest Guardian"
  job: "warrior"
  level: 10
  skills:
    - "slash"
    - "power_slash"
dialogues:
  - speaker: "elder"
    text: "용사여, 숲의 수호자를 무찌르시오"
  - speaker: "boss"
    text: "감히 내게 도전하는가!"
rewards:
  gold: 500
  items:
    - item_id: "rare_sword"
      quantity: 1
  experience: 1000
next_chapter: "chapter_2"
unlocks_job: null
```

## For AI Agents

### Working In This Directory
- 각 챕터는 순차 진행 (next_chapter 로 연결)
- 보스 정의: job, level, skills, gimmick 포함
- 보상: gold, items, experience, unlocks_job
- 대사: NPC/보스 인터랙션 정의

### Common Patterns
- boss.job: 보스가 사용할 직업 (스킬 결정)
- boss.level: 난이도 조정 (플레이어 추천 레벨)
- rewards: 클리어 후 획득 항목
- unlocks_job: 특정 챕터 클리어 시 직업 언락

## Dependencies
- src/story_mode/ - 챕터 로드 및 진행 관리
- src/character/ - 보스 캐릭터 인스턴스화
- src/combat/ - 보스 전투 실행

<!-- MANUAL: -->
