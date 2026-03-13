<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# data/tutorials/

## Purpose
튜토리얼 시스템 YAML 정의. 12개 튜토리얼 + 튜토리얼 설정. Step-based 진행, UI 오버레이, 조건부 활성화를 포함합니다.

## Key Files
| File | Description |
|------|-------------|
| tutorial_config.yaml | 튜토리얼 전역 설정 (활성화, 진행 추적) |
| 02_basic_interaction.yaml | 기본 상호작용 (NPC 대화, 상자 열기) |
| 06_skill_system.yaml | 스킬 시스템 (스킬 사용, 효과) |
| 07_job_system.yaml | 직업 시스템 (전직, 직업 변경) |
| 08_cooking.yaml | 요리 시스템 튜토리얼 |
| 09_alchemy.yaml | 연금술 시스템 튜토리얼 |
| 10_party_management.yaml | 파티 관리 튜토리얼 |
| 11_equipment_inventory.yaml | 장비/인벤토리 튜토리얼 |
| 12_dungeon_exploration.yaml | 던전 탐사 튜토리얼 |
| (03~05, 기타) | 추가 튜토리얼 |

## Structure Per File
```yaml
tutorial_id: "basic_interaction"
title: "기본 상호작용"
description: "NPC와 상호작용하고 상자를 여는 방법"
steps:
  - id: "talk_npc"
    type: "interaction"
    target: "npc_id_1"
    action: "talk"
    message: "NPC에게 말을 걸어보세요"
    condition:
      player_level: 1
  - id: "open_chest"
    type: "interaction"
    target: "chest_id_1"
    action: "open"
    message: "상자를 열어보세요"
    depends_on: "talk_npc"
enabled: true
auto_start: true
```

## For AI Agents

### Working In This Directory
- tutorial_config.yaml 가 모든 튜토리얼 목록 및 진행 상태 관리
- 각 튜토리얼은 step-based 시퀀스 (의존성 있음)
- tutorial_manager.py 가 YAML 로드 및 step 진행 추적
- UI overlay는 step message 를 화면에 표시

### Common Patterns
- step type: interaction (클릭), skill_use (스킬 사용), menu_open (메뉴) 등
- condition: player_level, job, item_count, inventory_space 등
- depends_on: 이전 step 완료 필수
- auto_start: true 면 조건 만족 시 자동 시작
- message: 플레이어에게 표시할 안내 메시지

## Dependencies
- src/tutorial/tutorial_manager.py - 튜토리얼 로드 및 진행 관리
- src/tutorial/tutorial_step.py - Step 데이터 클래스
- src/ui/npc_dialog_ui.py - 튜토리얼 UI 오버레이 렌더링

<!-- MANUAL: -->
