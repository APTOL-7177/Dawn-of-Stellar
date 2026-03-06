<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# achievement/

## Purpose
도전과제 및 마일스톤 시스템. 전투 통계 추적, 일일/주간 도전과제 생성, 카테고리별 도전과제 관리를 담당한다. 오마주·밈 테마의 유머러스한 도전과제를 포함한다.

## Key Files

| File | Description |
|------|-------------|
| `achievement_manager.py` | `AchievementManager` 클래스. 통계 추적(`stats` 딕셔너리), 일일 도전과제 생성, 전체 시스템 통합 관리자 |
| `achievement_system.py` | `AchievementSystem` 클래스. `Achievement` dataclass, `AchievementCategory` enum(COMBAT/EXPLORATION/CRAFTING/SOCIAL/HUMOROUS/MEME/HOMAGE), `AchievementRarity` enum |
| `milestone_system.py` | `MilestoneSystem` 클래스. `Milestone` dataclass. 장기 목표 추적 |

## For AI Agents

### Working In This Directory
- `AchievementManager`는 전역 인스턴스로 사용: `global_achievement_manager` (main 모듈에서 초기화)
- 통계 업데이트: `manager.stats["total_kills"] += 1` 패턴
- `AchievementCondition.type` 값: `"kill_count"`, `"damage_dealt_total"`, `"floor_progress"`, `"item_crafted"`, `"date_check"` 등
- 일일 도전과제: 매 세션 랜덤 3개 선택 (kills/damage/floor/cooking)
- 도전과제 완료 시 `AchievementRarity`에 따른 보상 차등
- 저장/로드는 `persistence/meta_progress.py`와 연동

### Testing Requirements
- 도전과제 진행도 테스트: 조건 충족 전/후 `is_complete` 검증
- 일일 도전과제 생성 테스트: 3개 선택 확인, 매번 다른 세트 생성 확인

### Common Patterns
```python
# 전투 통계 업데이트
achievement_manager.stats["total_kills"] += len(defeated_enemies)
achievement_manager.stats["total_damage_dealt"] += damage
achievement_manager.stats["max_damage_in_one_hit"] = max(
    achievement_manager.stats["max_damage_in_one_hit"], damage
)

# 도전과제 확인
achievement_manager.check_achievements()

# 층 진행 추적
achievement_manager.on_floor_reached(floor_number=10)
```

## Dependencies

### Internal
- `src.core.logger` — 도전과제 로그
- `src.persistence.meta_progress` — 도전과제 진행도 저장/로드

### External
- `datetime`: 일일 도전과제 날짜 체크
- `random`: 일일 도전과제 랜덤 선택

<!-- MANUAL: -->
