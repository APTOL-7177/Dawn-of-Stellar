# 게임에서 사용하는 사운드 파일 목록

이 문서는 Dawn of Stellar 게임에서 사용하는 모든 사운드 파일을 정리한 목록입니다.

## 목차
- [BGM (배경음악)](#bgm-배경음악)
- [SFX (효과음)](#sfx-효과음)
- [파일 경로](#파일-경로)

---

## BGM (배경음악)

BGM 파일은 `assets/audio/bg/` 디렉토리를 우선적으로 사용하며, 없을 경우 `assets/audio/me/` 디렉토리를 검색합니다. RPG MAKER MZ BGM/ME 사운드를 사용합니다.

### 메인 메뉴 & UI
| 트랙 이름 | 파일명 | 설명 |
|---------|--------|------|
| `intro` | `intro.ogg` | 인트로 스토리 |
| `main_menu` | `menu.ogg` | 메인 메뉴 |
| `menu` | `menu2.ogg` | 메뉴 |
| `party_setup` | `party_setup.ogg` | 파티 설정 |

### 월드 & 던전
| 트랙 이름 | 파일명 | 설명 |
|---------|--------|------|
| `world_map` | `worldmap.ogg` | 월드 맵 |
| `biome_0` | `caves.ogg` | 바이옴 0 (1-5층): 동굴 |
| `biome_1` | `forest.ogg` | 바이옴 1 (6-10층): 숲 |
| `biome_2` | `devillands.ogg` | 바이옴 2 (11-15층): 악마의 땅 |
| `biome_3` | `badlands.ogg` | 바이옴 3 (16-20층): 황무지 |
| `biome_4` | `desert.ogg` | 바이옴 4 (21-25층): 사막 |
| `biome_5` | `frostlands.ogg` | 바이옴 5 (26-30층): 얼음 땅 |
| `biome_6` | `highlands.ogg` | 바이옴 6 (31-35층): 고원 |
| `biome_7` | `icelands.ogg` | 바이옴 7 (36-40층): 빙원 |
| `biome_8` | `warlands.ogg` | 바이옴 8 (41-45층): 전쟁의 땅 |
| `biome_9` | `caves.ogg` | 바이옴 9 (46-50층): 동굴 (순환) |

### 전투
| 트랙 이름 | 파일명 | 설명 |
|---------|--------|------|
| `battle_normal` | `battle.ogg` | 일반 전투 |
| `battle_boss` | `boss.ogg` | 보스 전투 |
| `battle_sephiroth` | `sephiroth.ogg` | 세피로스 전투 |

### 전투 결과
| 트랙 이름 | 파일명 | 설명 |
|---------|--------|------|
| `victory` | `fanfare.ogg` | 승리 |
| `game_over` | `gameover.ogg` | 게임 오버 |

### 휴식 & 이벤트
| 트랙 이름 | 파일명 | 설명 |
|---------|--------|------|
| `rest` | `inn1.ogg` | 휴식 |

---

## SFX (효과음)

SFX 파일은 `assets/audio/se/` 디렉토리를 우선적으로 사용하며, 없을 경우 `assets/audio/sfx/` 디렉토리를 검색합니다. RPG MAKER MZ SE (Sound Effects)를 사용합니다.

### UI 효과음
| SFX 이름 | 파일명 | 설명 |
|---------|--------|------|
| `cursor_move` | `Cursor1.ogg` | 커서 이동 |
| `cursor_select` | `Decision1.ogg` | 메뉴 선택/확인 |
| `cursor_cancel` | `Cancel1.ogg` | 메뉴 취소/뒤로 |
| `cursor_error` | `Buzzer1.ogg` | 불가능한 행동 |
| `menu_open` | `Open1.ogg` | 메뉴 열기 |
| `menu_close` | `Close1.ogg` | 메뉴 닫기 |

### 전투 효과음
| SFX 이름 | 파일명 | 설명 |
|---------|--------|------|
| `attack_physical` | `Sword1.ogg` | 물리 공격 |
| `attack_gun` | `Gun1.ogg` | 총 공격 |
| `attack_magic` | `Magic1.ogg` | 마법 공격 |
| `damage_low` | `Damage1.ogg` | 낮은 데미지 |
| `damage_high` | `Damage3.ogg` | 높은 데미지 |
| `critical` | `Critical.ogg` | 크리티컬 히트 |
| `miss` | `Miss.ogg` | 회피/빗나감 |
| `dodge` | `Evasion1.ogg` | 회피 |
| `break` | `Break.ogg` | BRV BREAK/보스 죽음 |
| `guard` | `Parry.ogg` | 방어 |
| `battle_start` | `Battle1.ogg` | 전투 시작 |
| `escape` | `Run.ogg` | 도주 |
| `turn_start` | `Cursor2.ogg` | 턴 시작 |

### 캐릭터 상태 효과음
| SFX 이름 | 파일명 | 설명 |
|---------|--------|------|
| `hp_heal` | `Heal1.ogg` | HP 회복 |
| `hp_heal_high` | `Heal3.ogg` | 높은 HP 회복 |
| `hp_heal_max` | `Heal5.ogg` | 최대 HP 회복 |
| `mp_heal` | `Mana1.ogg` | MP 회복 |
| `level_up` | `Powerup.ogg` | 레벨업 |
| `status_buff` | `Up1.ogg` | 버프 적용 |
| `status_debuff` | `Down1.ogg` | 디버프 적용 |
| `death` | `Collapse1.ogg` | 전투불능 |
| `revive` | `Raise1.ogg` | 부활 |
| `faint` | `Paralyze1.ogg` | 기절 |

### 스킬 효과음
| SFX 이름 | 파일명 | 설명 |
|---------|--------|------|
| `cast_start` | `Magic1.ogg` | 스킬 시전 시작 |
| `cast_complete` | `Magic2.ogg` | 스킬 시전 완료 |
| `fire` | `Fire1.ogg` | 파이어 |
| `fire2` | `Fire2.ogg` | 파이어2 |
| `fire3` | `Fire3.ogg` | 파이어3 |
| `bolt` | `Thunder1.ogg` | 볼트 |
| `bolt2` | `Thunder2.ogg` | 볼트2 |
| `bolt3` | `Thunder3.ogg` | 볼트3 |
| `ice` | `Ice1.ogg` | 아이스 |
| `ice3` | `Ice3.ogg` | 아이스3 |
| `cure` | `Heal1.ogg` | 케어 |
| `haste` | `Up2.ogg` | 헤이스트 |
| `slow` | `Down2.ogg` | 슬로우 |
| `shell` | `Barrier.ogg` | 쉘 |
| `protect` | `Barrier.ogg` | 프로텍트 |
| `reflect` | `Reflection.ogg` | 리플렉트 |
| `ultima` | `Explosion4.ogg` | 알테마 |
| `flare` | `Explosion3.ogg` | 플레어 |
| `summon` | `Summon.ogg` | 소환 |
| `limit_break` | `Critical.ogg` | 리미트 브레이크 |
| `computer` | `Computer.ogg` | 컴퓨터 (해커) |
| `machine` | `Machine.ogg` | 기계 |
| `laser` | `Laser1.ogg` | 레이저 |
| `switch` | `Switch1.ogg` | 스위치 |
| `load` | `Load1.ogg` | 로드 |
| `save` | `Save1.ogg` | 세이브 |
| `bell` | `Bell1.ogg` | 벨 (바드) |
| `sound1` | `Sound1.ogg` | 사운드1 |
| `sound2` | `Sound2.ogg` | 사운드2 |
| `sound3` | `Sound3.ogg` | 사운드3 |
| `roar` | `Roar1.ogg` | 포효 (드래곤나이트) |
| `slash` | `Slash1.ogg` | 베기 |
| `slash2` | `Slash2.ogg` | 베기2 |
| `sword` | `Sword2.ogg` | 검 |
| `gun_shot` | `Gun1.ogg` | 총 발사 |
| `gun_reload` | `Gun2.ogg` | 총 장전 (해적) |
| `cannon` | `Explosion2.ogg` | 대포 (해적) |
| `wind` | `Wind1.ogg` | 바람 |
| `earth` | `Earth1.ogg` | 땅 |
| `holy` | `Heal4.ogg` | 성스러운 (팔라딘) |
| `dark` | `Dark1.ogg` | 어둠 (다크나이트) |
| `poison` | `Poison1.ogg` | 독 |
| `confusion` | `Confusion1.ogg` | 혼란 |

### 아이템 효과음
| SFX 이름 | 파일명 | 설명 |
|---------|--------|------|
| `get_item` | `Item1.ogg` | 아이템 획득 |
| `use_item` | `Item2.ogg` | 아이템 사용 |
| `open_chest` | `Chest1.ogg` | 상자 열기 |
| `get_gil` | `Coin.ogg` | 길 획득 |
| `equip` | `Equip1.ogg` | 장비 착용 |
| `buy` | `Shop1.ogg` | 구매 |
| `potion` | `Heal1.ogg` | 포션 |
| `high_potion` | `Heal3.ogg` | 하이 포션 |
| `elixir` | `Heal5.ogg` | 엘릭서 |
| `phoenix_down` | `Raise1.ogg` | 부활약 |
| `grenade` | `Explosion1.ogg` | 수류탄 |

### 월드 효과음
| SFX 이름 | 파일명 | 설명 |
|---------|--------|------|
| `door_open` | `Door1.ogg` | 문 열림 |
| `door_close` | `Close1.ogg` | 문 닫힘 |
| `gate_open` | `Gate1.ogg` | 게이트 열기 |
| `gate_unlock` | `Key.ogg` | 게이트 잠금 해제 |
| `stairs` | `Move1.ogg` | 계단 이동 |
| `save` | `Save1.ogg` | 세이브 |
| `gathering` | `Item2.ogg` | 채집 |
| `jump` | `Jump1.ogg` | 점프 |
| `land` | `Move2.ogg` | 착지 |
| `fall` | `Fall.ogg` | 낙하 |
| `switch_on` | `Switch1.ogg` | 스위치 켜기 |
| `alert` | `Siren.ogg` | 경보 |
| `break_open` | `Hammer.ogg` | 부수기 |

---

## 파일 경로

### BGM 파일
BGM은 다음 우선순위로 검색됩니다:
1. `assets/audio/bg/{BGM 파일명}.ogg` (최우선)
2. `assets/audio/me/{BGM 파일명}.ogg` (2순위)
3. `assets/audio/bgm/{BGM 파일명}.mp3` (3순위, 아카이브)

### SFX 파일
SFX는 다음 우선순위로 검색됩니다:
1. `assets/audio/se/{SFX 파일명}.ogg` (최우선)
2. `assets/audio/sfx/{SFX 파일명}.wav` (2순위, 아카이브)

AudioManager는 `.ogg`, `.mp3`, `.wav`, `.flac`, `.m4a` 확장자를 지원하며, 확장자가 없으면 자동으로 검색합니다.

### 설정 파일
모든 사운드 파일 매핑은 `config.yaml` 파일의 `audio` 섹션에 정의되어 있습니다:
- BGM: `audio.bgm.tracks`
- SFX: `audio.sfx.{category}.{sfx_name}`

---

## 참고 사항

1. **파일 확장자**: AudioManager는 `.ogg`, `.mp3`, `.wav`, `.flac`, `.m4a` 확장자를 지원합니다.
2. **SFX 캐싱**: 자주 사용하는 SFX는 메모리에 캐싱되어 있습니다.
3. **볼륨 제어**: 마스터 볼륨, BGM 볼륨, SFX 볼륨을 각각 제어할 수 있습니다.
4. **직업별 유니크 SFX**: 각 직업마다 특색있는 SFX를 사용합니다:
   - 해커: computer, machine, laser, switch, load, save
   - 해적: gun_reload, cannon
   - 바드: bell, sound1-3
   - 드래곤나이트: roar

---

## 실제 코드에서 사용되는 SFX

다음은 코드에서 실제로 호출되는 SFX 목록입니다:

### UI
- `ui.cursor_move` - 커서 이동 시
- `ui.cursor_select` - 메뉴 선택 시
- `ui.cursor_cancel` - 취소 시
- `ui.cursor_error` - 에러 발생 시
- `ui.menu_open` - 메뉴 열기 시
- `ui.menu_close` - 메뉴 닫기 시

### 전투
- `combat.miss` - 공격 빗나감
- `combat.attack_physical` - 물리 공격
- `combat.damage_high` - 높은 데미지
- `combat.battle_start` - 전투 시작
- `combat.turn_start` - 턴 시작

### 스킬
- `skill.cast_start` - 스킬 시전 시작
- `skill.cast_complete` - 스킬 시전 완료
- 스킬별 SFX (스킬 정의에 따라)

### 캐릭터
- `character.hp_heal` - HP 회복
- `character.status_buff` - 버프 적용
- 마법 공격/물리 공격 시 각각의 SFX

---

*최종 업데이트: 2024년*
