# 멀티플레이 메타 진행 규칙

## 개요

멀티플레이에서 메타 진행 상태는 각 플레이어마다 독립적으로 관리되며, 일부 요소는 호스트 기준으로 적용됩니다.

---

## 1. 특성 (Trait)

### 정의
- 각 캐릭터 직업별로 가지는 **개별 특성**
- 예: 전사의 "전투 마스터", 성직자의 "치유의 힘" 등
- 캐릭터별로 최대 2개 선택

### 멀티플레이 규칙
- **각 플레이어가 자신의 캐릭터에 대해 선택**
- 각 플레이어의 메타 진행 파일에서 특성 해금 상태 확인
- 특성 해금 여부: `meta.is_trait_unlocked(job_id, trait_id)`

### 구현 위치
- `src/ui/party_setup.py`: 파티 설정 UI에서 각 플레이어가 자신의 캐릭터를 만들 때 특성 선택
- `src/multiplayer/party_setup.py`: 멀티플레이 파티 설정 (각 플레이어별 직업 선택)

---

## 2. 캐릭터 해금 (Job Unlock)

### 정의
- 게임에서 사용 가능한 직업 목록
- 메타 진행에서 별의 파편으로 해금

### 멀티플레이 규칙
- **각 플레이어의 메타 진행 파일 기준으로 확인**
- 각 플레이어는 자신이 해금한 직업만 선택 가능
- 직업 해금 여부: `meta.is_job_unlocked(job_id)`

### 구현 위치
- `src/multiplayer/party_setup.py._load_jobs()`: 각 클라이언트에서 자신의 메타 진행 확인
- `src/ui/party_setup.py._load_jobs()`: 싱글플레이/멀티플레이 공통 로직

---

## 3. 패시브 (Passive)

### 정의
- 파티 전체에 적용되는 **공통 버프**
- 예: "HP 증폭", "신속", "힘의 축복" 등
- 코스트 시스템 (최대 10 코스트, 최대 3개)

### 멀티플레이 규칙
- **호스트가 선택** (파티 전체 공통)
- 패시브 해금 여부: `passives.yaml`의 `unlocked` 속성 (기본 해금)

### 구현 위치
- `src/ui/passive_selection.py`: 패시브 선택 UI
- `src/multiplayer/party_setup.py`: 멀티플레이 파티 설정 (호스트가 패시브 선택)
- 패시브 효과 적용: 캐릭터 생성 시 또는 전투 시작 시

---

## 4. 파티 강화 업그레이드 (Party Upgrades)

### 정의
- 파티 전체에 적용되는 **영구 강화 효과**
- 예: "HP 증가 I" (파티원 전체의 최대 HP +10%), "경험치 부스트 I" (획득 경험치 +10%) 등
- 상점에서 별의 파편으로 구매 가능한 영구 업그레이드

### 멀티플레이 규칙
- **호스트의 메타 진행 기준으로 적용**
- 호스트가 구매한 업그레이드(`purchased_upgrades`)만 파티 전체에 적용
- 업그레이드 확인: `host_meta.is_upgrade_purchased(upgrade_id)`

### 적용 시점
- 게임 시작 시 (캐릭터 생성 시)
- 모든 파티원의 캐릭터에 적용

### 구현 위치
- `src/ui/shop_ui.py`: 업그레이드 구매 UI
- `src/persistence/meta_progress.py`: 메타 진행 관리
- 업그레이드 효과 적용: 캐릭터 생성 시 또는 게임 시작 시

---

## 요약

| 요소 | 멀티플레이 규칙 | 기준 |
|------|---------------|------|
| **특성 (Trait)** | 각 플레이어가 자신의 캐릭터에 대해 선택 | 각 플레이어의 메타 진행 |
| **캐릭터 해금** | 각 플레이어가 자신이 해금한 직업만 선택 가능 | 각 플레이어의 메타 진행 |
| **패시브 선택** | 호스트가 선택 (파티 전체 공통) | 호스트 |
| **파티 강화 업그레이드** | 호스트의 메타 진행 기준으로 적용 | 호스트의 메타 진행 (`purchased_upgrades`) |

---

## 구현 세부사항

### 특성 선택
```python
# 각 플레이어가 자신의 캐릭터를 만들 때
meta = get_meta_progress()  # 각 플레이어의 메타 진행
unlocked_traits = [trait for trait in all_traits 
                   if meta.is_trait_unlocked(job_id, trait.id)]
```

### 직업 해금 확인
```python
# 각 플레이어가 직업을 선택할 때
meta = get_meta_progress()  # 각 플레이어의 메타 진행
available_jobs = [job for job in all_jobs 
                  if meta.is_job_unlocked(job.id)]
```

### 파티 강화 업그레이드 적용
```python
# 게임 시작 시 또는 캐릭터 생성 시
host_meta = get_meta_progress()  # 호스트의 메타 진행

# 호스트가 구매한 업그레이드 확인
if host_meta.is_upgrade_purchased("hp_boost_1"):
    # 모든 파티원의 HP +10%
    for character in party:
        character.max_hp = int(character.max_hp * 1.1)
        character.current_hp = int(character.current_hp * 1.1)

if host_meta.is_upgrade_purchased("exp_boost_1"):
    # 경험치 획득량 +10% (게임 통계에 적용)
    experience_multiplier = 1.1
```

---

## 참고

- 싱글플레이에서는 플레이어 한 명의 메타 진행만 사용
- 멀티플레이에서는 각 플레이어가 자신의 메타 진행을 사용하되, 패시브 강화만 호스트 기준

