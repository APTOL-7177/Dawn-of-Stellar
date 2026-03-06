<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# persistence

## Purpose
게임 상태를 JSON 파일로 저장/로드하는 시스템과, 게임 런 간에 영구 유지되는 메타 진행 상태(별의 파편, 영구 업그레이드, 마을 시설 레벨)를 관리한다.

## Key Files
| File | Description |
|------|-------------|
| `save_system.py` | `SaveSystem` 클래스 - JSON 기반 게임 저장/로드, 싱글/멀티플레이어 별도 파일 관리 |
| `meta_progress.py` | `MetaProgress` 데이터클래스 - 런 간 영구 유지 데이터 (별의 파편, 해금 특성, 시설 레벨, 창고) |
| `__init__.py` | 모듈 공개 인터페이스 |

## For AI Agents

### Working In This Directory
- 저장 파일 경로: `user_data/saves/save_single.json` (싱글), `user_data/saves/save_multiplayer.json` (멀티)
- 저장 시 버전(`"5.0.0"`)과 저장 시각 자동 추가
- `MetaProgress` 영구 데이터:
  - `star_fragments`: 메타 화폐
  - `unlocked_traits`: `{job_id: [trait_id, ...]}` 해금 특성
  - `purchased_upgrades`, `purchased_passives`: 구매 목록 (`Set[str]`)
  - `facility_levels`: 마을 시설 레벨 (game over 후에도 유지)
  - `hub_storage`, `town_storage`: 영구 창고 아이템
  - `tutorial_completed`: 튜토리얼 클리어 여부 (True면 재입장 불가)
- `get_meta_progress()` 싱글톤 함수로 전역 접근
- 저장 실패 시 `bool` 반환으로 오류 처리

### Testing Requirements
- 저장 후 로드 시 데이터 일치 확인
- `MetaProgress` 직렬화/역직렬화 (Set → List 변환 주의)
- 파일 없을 때 기본값 반환 확인

### Common Patterns
```python
from src.persistence.save_system import SaveSystem
from src.persistence.meta_progress import get_meta_progress

# 게임 저장
save_sys = SaveSystem()
success = save_sys.save_game("slot1", game_state, is_multiplayer=False)

# 메타 진행 상태 접근
meta = get_meta_progress()
meta.star_fragments += 10
meta.save()
```

## Dependencies

### Internal
- `src.core.logger` - 로깅

### External
- `json`, `pathlib`, `datetime`, `dataclasses` - 표준 라이브러리

<!-- MANUAL: -->
