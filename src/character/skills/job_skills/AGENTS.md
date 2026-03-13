<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 -->

# character/skills/job_skills - 35개 직업 스킬 구현

## Purpose

35개 직업별 스킬 구현. 각 직업의 고유 스킬, 궁극기, 팀워크 스킬을 Python 클래스로 정의합니다.

## Key Files (35 직업)

| File | Description |
|------|-------------|
| `warrior_skills.py` | 전사 (기본 공격 강화, 원거리 반사) |
| `berserker_skills.py` | 광전사 (광폭화, 데미지 증가) |
| `knight_skills.py` | 기사 (방어, 파티 보호) |
| `paladin_skills.py` | 성기사 (신성 공격, 치유) |
| `dark_knight_skills.py` | 암흑기사 (암흑 공격, HP 소비) |
| `dragon_knight_skills.py` | 용기사 (용의 힘) |
| `samurai_skills.py` | 사무라이 (상태이상 활용) |
| `gladiator_skills.py` | 검투사 (경기장 전투) |
| `archer_skills.py` | 궁수 (원거리 공격, 지원 사격) |
| `sniper_skills.py` | 저격수 (정밀 공격) |
| `pirate_skills.py` | 해적 (약탈, 원거리) |
| `rogue_skills.py` | 로그 (은폐, 독) |
| `assassin_skills.py` | 암살자 (암습 공격) |
| `magician_skills.py` | 마법사 (기본 마법) |
| `archmage_skills.py` | 대마법사 (고등 마법) |
| `battle_mage_skills.py` | 전투 마법사 (마법 + 물리) |
| `spellblade_skills.py` | 스펠블레이드 (검 + 마법) |
| `elementalist_skills.py` | 정령술사 (속성 마법) |
| `time_mage_skills.py` | 시간 마법사 (시간 조작) |
| `dimensionist_skills.py` | 차원술사 (차원 이동) |
| `illusionist_skills.py` | 환술사 (미환, 혼란) |
| `priest_skills.py` | 사제 (치유, 부활) |
| `cleric_skills.py` | 성직자 (신성 힐) |
| `druid_skills.py` | 드루이드 (자연 마법) |
| `shaman_skills.py` | 무당 (영혼 소환) |
| `monk_skills.py` | 수도사 (격투, 선수 증진) |
| `breaker_skills.py` | 브레이커 (브레이크 스킬) |
| `philosopher_skills.py` | 철학자 (지혜 기반) |
| `hacker_skills.py` | 해커 (정보 조작) |
| `engineer_skills.py` | 엔지니어 (기계 장치) |
| `alchemist_skills.py` | 연금술사 (약물, 변환) |
| `bard_skills.py` | 음유시인 (곡, 강화) |
| `necromancer_skills.py` | 강령술사 (죽음 마법) |
| `vampire_skills.py` | 흡혈귀 (흡수, 장수) |
| `sword_saint_skills.py` | 검성 (검 마스터) |

## For AI Agents

### Working In This Directory

- **스킬 추가**: 직업 파일의 `@register_skill()` 데코레이터로 등록
- **스킬 수정**: 각 함수의 매개변수(코스트, 효과) 조정
- **직업 능력치 링크**: `character/job_stats_loader.py`와 동기화
- **궁극기 추가**: `ultimate` 태그로 마크된 스킬 추가

### Testing Requirements

- 직업 로드 테스트: 모든 직업의 스킬이 등록되는지 확인
- 스킬 사용 테스트: 각 직업의 대표 스킬 동작 확인
- 팀워크 스킬 테스트: 파티원 스킬 상호작용
- 밸런싱 테스트: 직업 간 DPS, 탱킹, 힐 능력 비교

### Common Patterns

- 스킬 등록 데코레이터 (`@register_skill()`)
- 스킬 빌더 패턴 (Skill 객체 구성)
- 직업별 매개변수 (기믹 코스트, 기본 데미지)
- 궁극기 마크 (턴 제한, 제한된 MP)

## Dependencies

### Internal
- `../skill.py` - Skill 클래스
- `../skill_manager.py` - 스킬 등록
- `../../character/character.py` - 캐릭터 능력치
- `../../character/stats.py` - 능력치 계산
- `../../combat/damage_calculator.py` - 데미지 계산
- `../costs/` - MP, HP, 기믹 코스트
- `../effects/` - 데미지, 버프, 상태이상 효과

### External
- `data/skills/` - 스킬 YAML 정의 (선택사항)

<!-- MANUAL: -->
