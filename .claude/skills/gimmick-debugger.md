# Gimmick Debugger Skill

직업 기믹 시스템 디버깅 전문 스킬

## 목적
- 33개+ 직업의 고유 기믹 오동작 진단
- 기믹 조건 판정 로직 검증
- 기믹-트레이트 연동 확인
- 기믹 UI 표시 문제 해결

## 핵심 파일 맵

| 역할 | 파일 | 크기 |
|------|------|------|
| 기믹 초기화/업데이트/렌더 | `src/character/gimmick_updater.py` | ~333KB |
| 기믹-트레이트 연동 효과 | `src/character/gimmick_trait_effects.py` | ~50KB |
| 트레이트 효과 전체 | `src/character/trait_effects.py` | ~211KB |
| 기믹 데이터 정의 | `data/characters/<job>.yaml` → `gimmick:` 섹션 |
| 전투 중 기믹 훅 | `src/combat/combat_manager.py` |

## 기믹 타입별 키워드

```
검투사: crowd_cheer, 관중, 환호, crowd_demand
궁수: support_fire, 마킹, mark, arrow
사무라이: yomi, 예측, prediction, toggle
배틀메이지: rune_signal, 룬, detonation
기사: duty, 의무, oath
프리스트: faith, miracle, 신앙
도적/시프: steal, furtum, 푸르툼
```

## 디버깅 절차

### 1. YAML 데이터 확인
```bash
# 기믹 정의 확인
python -c "import yaml; d=yaml.safe_load(open('data/characters/<job>.yaml',encoding='utf-8')); print(yaml.dump(d.get('gimmick',{}), allow_unicode=True))"
```

### 2. 기믹 메서드 검색
```
grep_search: gimmick_updater.py → "_initialize_<gimmick_type>"
grep_search: gimmick_updater.py → "_update_<gimmick_type>"
grep_search: gimmick_updater.py → "_render_<gimmick_type>"
```

### 3. 이벤트 훅 추적
combat_manager.py에서 기믹 업데이트 호출 지점:
- `_update_gimmick()` → 턴/라운드 전환 시
- `on_skill_used()` → 스킬 사용 후
- `on_damage_dealt()` → 데미지 적용 후
- `on_kill()` → 적 처치 시
- `on_hit()` → 피격 시

### 4. 일반적 원인
- **조건 미충족**: context에 필요한 키(action_type, target_id, hp_percent 등)가 누락
- **타이밍 문제**: 라운드 vs 턴 구분 오류 (라운드 = 전체 한 바퀴, 턴 = 개별 행동)
- **경계값 오류**: `>` vs `>=`, 0 기반 vs 1 기반 인덱싱
- **게이지 캡**: min/max 클램핑 누락 또는 잘못된 범위
- **UI 미갱신**: 기믹 상태 변경 후 렌더링 미호출
