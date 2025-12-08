# 6직업 리메이크 구현 TODO

## 작업 순서
1. 정령술사 → 2. 검투사 → 3. 해커 → 4. 성기사 → 5. 신관 → 6. 도적

---

## 1. 정령술사 (Elementalist) - 정령 전환 시스템

### YAML 데이터
- [ ] `data/characters/elementalist.yaml` 업데이트
  - [ ] 정령 공명 효과 추가 (6가지 조합)
  - [ ] 정령 자동 교체 로직 명시

### 스킬 YAML
- [ ] `data/skills/summon_fire.yaml` 업데이트 (MP 12)
- [ ] `data/skills/summon_water.yaml` 업데이트 (MP 10)
- [ ] `data/skills/summon_wind.yaml` 업데이트 (MP 10)
- [ ] `data/skills/summon_earth.yaml` 업데이트 (MP 10)
- [ ] `data/skills/fusion_firestorm.yaml` - 화염+바람 (화염 돌풍)
- [ ] `data/skills/fusion_steam.yaml` - 화염+물 (증기 폭발)
- [ ] `data/skills/fusion_lava.yaml` - 화염+대지 (용암 분출) [신규]
- [ ] `data/skills/fusion_blizzard.yaml` - 물+바람 (얼음 폭풍) [신규]
- [ ] `data/skills/fusion_mudtrap.yaml` - 물+대지 (진흙 속박)
- [ ] `data/skills/fusion_sandstorm.yaml` - 바람+대지 (모래 폭풍) [신규]
- [ ] `data/skills/spirit_release.yaml` - 정령 해방 [신규]
- [ ] `data/skills/spirit_swap.yaml` - 정령 교대 [신규]
- [ ] `data/skills/natures_law.yaml` - 자연의 섭리 [신규]
- [ ] `data/skills/elementalist_ultimate.yaml` - 4대 정령의 합일 업데이트
- [ ] `data/skills/elementalist_teamwork.yaml` - 4대 정령의 축복 업데이트

### 로직
- [ ] `src/character/gimmick_updater.py` - 정령 공명 효과 적용 로직
- [ ] `src/character/skills/effects/gimmick_effect.py` - 정령 자동 교체 로직

### 특성
- [ ] 화염 정령의 분노: 화상 +50%
- [ ] 물 정령의 은총: 힐 시 MP +5
- [ ] 바람 정령의 가호: 회피 시 ATB +25
- [ ] 대지 정령의 축복: 피격 시 15% 무효화
- [ ] 이중 정령 숙련: 융합 MP -25%, 데미지 +15%

---

## 2. 검투사 (Gladiator) - 콜로세움 쇼타임 시스템

### YAML 데이터
- [ ] `data/characters/gladiator.yaml` 전면 개편
  - [ ] 관중의 요구 시스템
  - [ ] 환호 5단계 (무명/신인/인기검투사/챔피언/전설)
  - [ ] 그랜드 피날레 3가지 선택

### 스킬 YAML
- [ ] 투기장 강타 (arena_strike)
- [ ] 화려한 일격 (spectacular_strike)
- [ ] 도발 (taunt) - 리메이크
- [ ] 투기의 자세 (fighting_stance)
- [ ] 반격 준비 (counter_ready)
- [ ] 기대치 조절 (adjust_expectation) [신규]
- [ ] 관중 선동 (crowd_incite) [신규]
- [ ] 처형 선언 (execution_declare) [신규]
- [ ] 피의 축제 (blood_festival) - 환호 30+
- [ ] 챔피언의 포효 (champion_roar) - 환호 60+
- [ ] 불멸의 투혼 (immortal_spirit) - 환호 80+
- [ ] 그랜드 피날레 (grand_finale) - 환호 100
- [ ] 팀워크: 콜로세움의 전설들

### 로직
- [ ] `src/combat/crowd_demand_system.py` [신규] - 관중의 요구 시스템
- [ ] `src/character/gimmick_updater.py` - 환호 단계별 효과
- [ ] `src/combat/counter_system.py` - 완벽한 반격 로직

### 특성
- [ ] 군중의 총아 (요구 충족 시 추가 환호 +5)
- [ ] 화려한 전투가 (환호 80+ 듀얼 스트라이크)
- [ ] 쇼맨십 (크리 시 다음 공격 필중)
- [ ] 군중 반응 (처치 +25, 피격 -5)
- [ ] 도전자 [신규] (보스전 환호 +50%)
- [ ] 쇼스토퍼 [신규] (야유 페널티 50% 감소)

---

## 3. 해커 (Hacker) - 침투 시스템

### YAML 데이터
- [ ] `data/characters/hacker.yaml` 전면 개편
  - [ ] 침투 게이지 (적별 개별 관리)
  - [ ] RAM 자원 시스템 (최대 8GB)
  - [ ] 침투 단계별 디버프

### 스킬 YAML
- [ ] 핑 공격 (ping_attack)
- [ ] 포트 스캔 (port_scan)
- [ ] SQL 인젝션 (sql_injection)
- [ ] 패킷 스니핑 (packet_sniffing)
- [ ] DDoS 공격 (ddos_attack)
- [ ] 피싱 공격 (phishing_attack)
- [ ] 제로데이 (zero_day)
- [ ] 스캐너 실행 (run_scanner)
- [ ] 트로이 목마 (trojan_horse)
- [ ] 웜 배포 (deploy_worm)
- [ ] 랜섬웨어 (ransomware)
- [ ] 키로거 (keylogger)
- [ ] 루트킷 (rootkit)
- [ ] RAM 확장 (ram_expand)
- [ ] 오버클럭 (overclock)
- [ ] 방화벽 (firewall)
- [ ] VPN 터널 (vpn_tunnel)
- [ ] 장악: 시스템 크래시 (system_crash)
- [ ] 장악: 데이터 와이프 (data_wipe)
- [ ] 장악: 바이러스 폭발 (virus_explosion)
- [ ] 장악: 메모리 덤프 (memory_dump)
- [ ] 궁극기: 시스템 전면 장악
- [ ] 팀워크: 분산 해킹 네트워크

### 로직
- [ ] `src/combat/intrusion_system.py` [신규] - 침투 게이지 관리
- [ ] `src/character/gimmick_updater.py` - RAM 회복 로직
- [ ] `src/character/skills/effects/intrusion_effect.py` [신규]

### 특성
- [ ] 병렬 처리: RAM +1/턴
- [ ] 침투 전문가: 침투 +20%
- [ ] 백도어 마스터: 침투 25%+ 크리 +15%
- [ ] 익스플로잇: 침투 75%+ 피해 +25%
- [ ] 봇넷: 침투 100% 시 전파 +20
- [ ] 제로데이 헌터: 전투 시작 시 무작위 +30
- [ ] 가상화: 오버클럭 HP 페널티 -50%
- [ ] 메모리 누수: 장악 후 RAM +2

---

## 4. 성기사 (Paladin) - 서약 시스템

### YAML 데이터
- [ ] `data/characters/paladin.yaml` 전면 개편
  - [ ] 서약 3종 (인내/순결/자비)
  - [ ] 신앙 게이지 (0~100)
  - [ ] 기적 스킬 해금 조건

### 스킬 YAML
- [ ] 서약 선언 (declare_oath) [신규]
- [ ] 신성 타격 (holy_strike)
- [ ] 심판의 빛 (judgment_light)
- [ ] 성스러운 방패 (holy_shield)
- [ ] 치유의 손길 (healing_touch)
- [ ] 축복 (blessing)
- [ ] 정화의 빛 (purifying_light)
- [ ] 성수 뿌리기 (holy_water)
- [ ] 기적: 작은 기적 (small_miracle) - 25+
- [ ] 기적: 보호의 기적 (protection_miracle) - 50+
- [ ] 기적: 치유의 기적 (healing_miracle) - 50+
- [ ] 기적: 부활의 기적 (resurrection_miracle) - 75+
- [ ] 기적: 정화의 기적 (purification_miracle) - 75+
- [ ] 기적: 신의 심판 (divine_judgment) - 100
- [ ] 기적: 신의 은총 (divine_grace) - 100
- [ ] 궁극기: 인내자의 승천 / 정화의 성역 / 무한한 자비 (서약별)
- [ ] 팀워크: 삼위일체의 축복

### 로직
- [ ] `src/combat/oath_system.py` [신규] - 서약 선택/변경/체크
- [ ] `src/character/gimmick_updater.py` - 서약 준수/위반 판정
- [ ] `src/ui/oath_selection_ui.py` [신규] - 서약 선택 UI
- [ ] 저장 시스템 연동 (paladin_oath 데이터)

### 특성
- [ ] 신성한 가호: 신앙 50+ 파티 치명타 무효화
- [ ] 성스러운 오라: 서약 준수 중 파티 방어 +20%
- [ ] 희생의 정신: 인내 서약 전용 대신 맞기 + 신앙 +15
- [ ] 치유의 빛: 자비 서약 전용 치유 시 신앙 +5
- [ ] 정의의 분노: 서약 위반 페널티 50% 감소

---

## 5. 신관 (Priest) - 신탁 시스템

### YAML 데이터
- [ ] `data/characters/priest.yaml` 전면 개편
  - [ ] 신탁 6종 (치유/심판/수호/정화/인내/침묵)
  - [ ] 신앙 게이지 (0~100)
  - [ ] 연속 충족 보너스

### 스킬 YAML
- [ ] 신탁 갱신 (oracle_refresh) [신규]
- [ ] 신성 타격 (holy_strike)
- [ ] 심판의 빛 (judgment_light)
- [ ] 치유의 손길 (healing_touch)
- [ ] 신성한 축복 (divine_blessing)
- [ ] 정화의 기도 (purification_prayer)
- [ ] 신의 방패 (divine_shield)
- [ ] 기도 (pray) - 대기 + MP 회복
- [ ] 기적: 작은 기적 (small_miracle) - 25+
- [ ] 기적: 수호의 기적 (guardian_miracle) - 50+
- [ ] 기적: 치유의 기적 (healing_miracle) - 50+
- [ ] 기적: 부활의 기적 (resurrection_miracle) - 75+
- [ ] 기적: 대정화 (great_purification) - 75+
- [ ] 기적: 신의 심판 (divine_judgment) - 100
- [ ] 기적: 신의 은총 (divine_grace) - 100
- [ ] 궁극기: 만신전의 심판 / 무한한 자비
- [ ] 팀워크: 신의 대리인

### 로직
- [ ] `src/combat/oracle_system.py` [신규] - 신탁 발생/충족 체크
- [ ] `src/character/gimmick_updater.py` - 신앙 게이지 관리
- [ ] `src/ui/oracle_ui.py` [신규] - 신탁 표시 UI
- [ ] 저장 시스템 연동 (priest_oracle 데이터)

### 특성
- [ ] 신탁의 예지: 다음 신탁 미리보기
- [ ] 이중 축복: 신탁 충족 30% 2배 신앙
- [ ] 신의 총애: 신앙 50+ 치유 +25%
- [ ] 고행자의 길: 인내/침묵 충족 시 HP 10% 회복
- [ ] 기적의 연쇄: 기적 후 다음 충족 시 신앙 -20 반환

---

## 6. 도적 (Rogue) - 농락 시스템

### YAML 데이터
- [ ] `data/characters/rogue.yaml` 전면 개편
  - [ ] 농락 스택 (적 단위, 최대 10)
  - [ ] 독 시스템 (4종 독, 최대 5중첩)
  - [ ] 농락-독 시너지

### 스킬 YAML
- [ ] 비수 난무 (blade_flurry) [신규]
- [ ] 독침 (poison_needle)
- [ ] 독 바르기 (apply_poison)
- [ ] 신경독 투척 (nerve_toxin)
- [ ] 그림자 밟기 (shadow_step) [신규]
- [ ] 기습 (ambush)
- [ ] 훔치기 (steal)
- [ ] 연막탄 (smoke_bomb)
- [ ] 독 폭발 (poison_explosion) [신규]
- [ ] 연쇄 감염 (chain_infection) [신규]
- [ ] 해독제 강탈 (antidote_steal) [신규]
- [ ] 조롱 (taunt_rogue) - 농락 3+
- [ ] 기만의 춤 (deception_dance) - 농락 5+
- [ ] 농락의 정점 (mockery_peak) - 농락 7+
- [ ] 완전한 무력화 (total_disable) - 농락 10
- [ ] 궁극기: 독살의 무도
- [ ] 팀워크: 협동 암살

### 로직
- [ ] `src/combat/mockery_system.py` [신규] - 농락 스택 관리
- [ ] `src/combat/poison_system.py` [신규] - 독 시스템 (4종, 중첩)
- [ ] `src/character/gimmick_updater.py` - 농락-독 시너지

### 특성
- [ ] 독술사: 독 데미지 +30%, 지속 +1턴
- [ ] 농락의 달인: 농락 획득량 +50%
- [ ] 민첩한 발놀림: 행동 후 50% 재행동 (1턴 1회)
- [ ] 독의 대가: 독 적 크리 +25%
- [ ] 그림자 잔상: 회피 성공 시 회피 불가 부여
- [ ] 치명적 약점: 농락 7+ 방어 무시 30%

---

## 진행 상황

| 직업 | 상태 | 완료일 |
|------|------|--------|
| 정령술사 | ✅ 완료 | 2025-12-03 |
| 검투사 | ✅ 완료 | 2025-12-03 |
| 해커 | ✅ 완료 | 2025-12-03 |
| 성기사 | ✅ 완료 | 2025-12-03 |
| 신관 | ✅ 완료 | 2025-12-03 |
| 도적 | ✅ 완료 | 2025-12-03 |

---

## 🎉 전체 리메이크 완료!

**완료일**: 2025-12-03
