<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# tests/integration/

## Purpose
통합 테스트. 여러 시스템이 함께 동작하는 시나리오를 검증합니다. 멀티플레이어, 전투-스킬 연동, 튜토리얼-게임 진행 등을 테스트합니다.

## Key Files
| File | Description |
|------|-------------|
| test_combat_flow.py | 전투 시작 -> 스킬 사용 -> 보상 획득 전체 흐름 |
| (추가 통합 테스트) | 멀티플레이어 동기화, 튜토리얼-RPG 연동 등 |

## Test Coverage
```
Integration tests:
  - test_combat_flow: 전투 입장 -> 턴 진행 -> 승리 -> 보상
  - test_multiplayer_combat_sync: P2P 전투 동기화
  - test_tutorial_story_flow: 튜토리얼 -> 스토리 -> RPG 연결
  - test_item_crafting_flow: 요리/합성 -> 인벤토리 -> 장비
```

## For AI Agents

### Working In This Directory
- 실제 게임 흐름 시뮬레이션
- 여러 모듈이 정합하는지 검증
- 데이터 흐름 (character -> skill -> combat -> inventory -> persistence)
- 멀티플레이어 P2P 네트워크 동기화

### Common Patterns
- Setup: 캐릭터, 아이템, 게임 상태 초기화
- Action: 전투, 스킬 사용, 아이템 획득 등 시뮬레이션
- Assertion: 최종 상태 검증 (HP, 보상, 인벤토리 등)
- Cleanup: 테스트 후 상태 정리

## Dependencies
- pytest
- src/ 모든 주요 모듈 (combat, character, inventory, multiplayer 등)
- data/ 게임 데이터 (YAML)
- src/persistence/ - 게임 상태 저장/로드

<!-- MANUAL: -->
