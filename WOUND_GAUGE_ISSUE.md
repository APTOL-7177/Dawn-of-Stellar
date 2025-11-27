# HP 게이지 상처 표시 문제 분석 및 해결 방안

## 📋 문제 상황

### 현재 문제
- **증상**: HP 게이지의 상처 영역이 검은색 또는 붉은색 블록으로 표시됨
- **예상 동작**: 빗금 패턴(검은색 줄무늬)이 게이지 배경색(HP 상태에 따라 짙은 초록/노랑/빨강) 위에 표시되어야 함
- **작동 환경**: 
  - ✅ `scripts/test_wound_gauge.py`에서는 정상 작동
  - ❌ 실제 게임(`src/ui/combat_ui.py`, `src/ui/world_ui.py`)에서는 문제 발생

### 시각적 문제
1. 빗금 사이의 배경색이 검은색으로 표시됨
2. 전체 상처 영역이 검은색 블록으로 보임
3. 게이지 배경색(초록/노랑/빨강)이 제대로 표시되지 않음

## 🔧 시도한 해결 방법들

### 1. 경계 타일 생성 로직 (Boundary Tile)
- **목적**: HP, 빈 영역, 상처가 모두 있는 셀을 하나의 커스텀 타일로 생성
- **구현**: `src/ui/gauge_tileset.py`의 `create_boundary_tile()` 메서드
- **결과**: ❌ 타일 내부 픽셀 데이터는 올바르지만 화면에는 여전히 검은색 블록 표시

### 2. 배경색 명시적 설정
- **목적**: 타일 내부에 배경색을 포함시켜 투명 부분 문제 해결
- **구현**: 
  - 타일 초기화 시 `bg_color`로 전체 채우기
  - 빗금 사이 부분을 `bg_color`로 명시적 설정
- **결과**: ❌ 로그상 타일 데이터는 올바르지만 렌더링 문제 지속

### 3. bg_blend 설정 변경
- **시도한 값들**:
  - `libtcodpy.BKGND_NONE`: 타일의 투명 부분 유지 → 실패
  - `libtcodpy.BKGND_SET`: 타일 내부 픽셀 데이터 강제 설정 → 실패
  - `libtcodpy.BKGND_ALPHA(255)`: 완전 불투명 → 실패
- **결과**: ❌ 모든 설정에서 문제 지속

### 4. 렌더링 순서 조정
- **목적**: 배경색을 먼저 채운 후 타일 오버레이
- **구현**: 
  ```python
  console.draw_rect(x + i, y, 1, 1, ch=ord(" "), bg=bg_color)
  console.print(x + i, y, tile_char, bg_blend=libtcodpy.BKGND_NONE)
  ```
- **결과**: ❌ 문제 지속

### 5. 경계 타일과 wound_stripe 타일 혼용
- **목적**: 경계 타일이 실패하면 `wound_stripe` 타일로 폴백
- **구현**: 조건부 분기로 두 가지 방식 모두 지원
- **결과**: ❌ 두 방식 모두 문제 지속

## 🔍 문제 원인 분석

### 1. 렌더링 순서 문제
- `render_space_background()`가 먼저 호출되어 전체 화면 배경을 그림
- 이후 게이지 렌더링 시 배경이 타일을 덮어쓰는 문제 가능성
- **위치**: `src/ui/combat_ui.py:1747` - `render_space_background()` 먼저 호출

### 2. 타일 등록/캐싱 문제
- 동적 타일 생성 시 LRU 캐시 사용
- 타일이 제대로 등록되지 않거나 캐시에서 제대로 조회되지 않을 가능성
- **위치**: `src/ui/gauge_tileset.py` - `_boundary_tile_cache`, `_boundary_tile_access_order`

### 3. TCOD 렌더러 차이
- 테스트 파일과 실제 게임의 렌더러 설정이 다를 수 있음
- OpenGL2, Direct3D11 등 렌더러별로 커스텀 타일 처리 방식이 다를 수 있음
- **위치**: `config.yaml`의 `display.renderer` 설정

### 4. 타일 내부 픽셀 데이터 vs 실제 렌더링
- 로그상 타일 내부 픽셀 데이터는 올바르게 설정됨
- 하지만 실제 화면 렌더링 시 다른 결과가 나옴
- TCOD의 타일 렌더링 파이프라인에서 문제 발생 가능성

## 📊 현재 코드 구조

### 경계 타일 생성 로직 (`src/ui/gauge_tileset.py`)
```python
def create_boundary_tile(...):
    # 1. 타일 전체를 bg_color로 초기화
    tile[:, :, 0:3] = bg_color
    tile[:, :, 3] = 255  # 완전 불투명
    
    # 2. HP 영역 그리기 (hp_pixels > 0일 때)
    
    # 3. 상처 영역 빗금 패턴 그리기
    # - 빗금: wound_stripe_color (검은색)
    # - 빗금 사이: bg_color (게이지 배경색)
    
    # 4. 빈 HP 영역: bg_color
```

### 게이지 렌더링 로직 (`src/ui/gauge_renderer.py`)
```python
elif cell_wound_pixels >= divisions and cell_hp_pixels == 0:
    # 상처가 셀 전체를 채움
    boundary_tile = tile_manager.create_boundary_tile(
        hp_pixels=0,
        wound_pixels=cell_wound_pixels,
        ...
    )
    console.print(x + i, y, boundary_tile, bg_blend=libtcodpy.BKGND_SET)
```

## 🎯 해결해야 할 핵심 문제

1. **빗금 사이의 배경색 표시**
   - 현재: 검은색 블록
   - 목표: 게이지 배경색(초록/노랑/빨강)

2. **타일 렌더링 일관성**
   - 테스트 파일에서는 작동하지만 실제 게임에서는 작동하지 않음
   - 렌더러 차이 또는 렌더링 순서 문제

3. **경계 타일 생성/등록 신뢰성**
   - 타일이 제대로 생성되고 등록되었는지 확인 필요
   - 캐시 문제 또는 codepoint 할당 문제 가능성

## 💡 다음 단계 제안

### 1. 디버깅 강화
- 타일이 실제로 등록되었는지 확인하는 로깅 추가
- 렌더링 직전/직후 타일 데이터 샘플링 및 로그 출력
- `render_space_background`와 게이지 렌더링 순서 비교

### 2. 렌더링 순서 변경 실험
- 게이지 렌더링을 `render_space_background` **이후**에 실행
- 또는 게이지 영역에 한해 배경 렌더링 스킵

### 3. 타일 생성 방식 단순화
- 경계 타일 대신 더 단순한 방식 시도
- 예: 배경색 셀 + 투명 빗금 타일 오버레이 방식으로 완전히 재구현

### 4. 테스트 파일과 실제 게임 환경 비교
- 테스트 파일의 렌더러 설정을 실제 게임과 동일하게 맞추기
- 테스트 파일에서도 `render_space_background` 호출 추가하여 동일 환경 조성

### 5. TCOD 문서 및 소스코드 확인
- 커스텀 타일 렌더링 시 `bg_blend` 동작 방식 확인
- 타일 내부 픽셀 데이터와 `console.print`의 `bg` 파라미터 상호작용 확인

## 📝 관련 파일

- `src/ui/gauge_renderer.py`: 게이지 렌더링 로직
- `src/ui/gauge_tileset.py`: 커스텀 타일 생성 및 관리
- `src/ui/combat_ui.py`: 전투 UI 렌더링 (render_space_background 호출)
- `src/ui/world_ui.py`: 월드 탐험 UI 렌더링
- `scripts/test_wound_gauge.py`: 테스트 파일 (정상 작동)
- `src/ui/tcod_display.py`: 배경 렌더링 함수

## 🔄 최근 변경 이력

1. 경계 타일 생성 로직 재도입
2. `BKGND_SET` 사용하여 타일 강제 덮어쓰기 시도
3. 배경색 명시적 전달 (`bg=bg_color`)
4. 폴백 로직 추가

**현재 상태**: 문제 지속, 근본 원인 미확인

## ❓ 확인 필요 사항

1. 타일이 실제로 등록되었는지 (codepoint 할당 확인)
2. 타일 렌더링 시 내부 픽셀 데이터가 실제로 사용되는지
3. `render_space_background`와의 상호작용 문제
4. 테스트 파일과 실제 게임의 환경 차이

