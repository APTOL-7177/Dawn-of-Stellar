<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# Pygame 백엔드

## 목적
TCOD 호환 렌더링을 Pygame으로 구현하는 커스텀 백엔드. 폰트 렌더링, 맵 조명, 특수 효과, 윈도우 관리, 콘솔 에뮬레이션을 포함합니다. 게임의 모든 시각 요소를 처리하며, effects/ 서브시스템으로 파티클, 스크린 효과, 전환 애니메이션을 지원합니다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| pygame_display.py | Pygame 윈도우 관리 및 렌더링 루프 |
| pygame_console.py | TCOD 콘솔 에뮬레이션 |
| pygame_context.py | Pygame 렌더링 컨텍스트 |
| font_atlas.py | 폰트 아틀라스 생성 및 관리 |
| gauge_tiles.py | HP/MP 게이지 타일 렌더링 |
| map_lighting.py | 동적 조명 및 FOV 계산 |
| event_adapter.py | Pygame 이벤트를 TCOD 이벤트로 변환 |
| window_manager.py | 윈도우 크기 조절, 전체화면 모드 |
| tooltip.py | 툴팁 렌더링 |
| tcod_shim.py | TCOD 호환성 레이어 |
| effects/ | 특수 효과 시스템 (서브시스템) |

## AI 에이전트를 위한 가이드
### 이 디렉토리에서 작업할 때
- Pygame 렌더링 파이프라인을 이해해야 합니다 (표면 생성 → 텍스처 렌더링 → 화면 업데이트).
- 모든 색상은 RGB 튜플 형식입니다.
- 성능 최적화는 중요합니다 (매 프레임 60fps 유지).
- effects/ 서브시스템과 밀접하게 통합됩니다.

### 테스트 요구사항
- 렌더링 변경은 시각적 검증이 필요합니다.
- 성능 변경은 프레임 레이트 측정으로 검증합니다.
- 폰트 렌더링은 다양한 해상도에서 검증합니다.

### 일반적인 패턴
- Pygame 표면은 더블 버퍼링으로 관리됩니다.
- 폰트는 아틀라스로 미리 렌더링됩니다 (성능).
- 조명은 FOV 맵과 연계되어 동적으로 계산됩니다.

## 의존성
### 내부
- `src/ui/pygame_backend/effects/` - 특수 효과
- `src/world/` - FOV, 맵 데이터
- `src/ui/` - UI 호출자

### 외부
- `pygame` - 게임 렌더링 라이브러리
- `tcod` - 호환성 참조

<!-- MANUAL: -->
