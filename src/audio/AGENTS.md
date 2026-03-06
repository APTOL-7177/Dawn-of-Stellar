<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# audio

## Purpose
pygame.mixer를 사용하여 BGM(배경음악)과 SFX(효과음)를 관리하는 오디오 시스템. 볼륨 제어, 페이드 인/아웃, 바이옴별 BGM 전환을 지원한다.

## Key Files
| File | Description |
|------|-------------|
| `audio_manager.py` | `AudioManager` 클래스 - BGM/SFX 재생, 볼륨 관리, SFX 캐시, PyInstaller 경로 처리 |
| `__init__.py` | 모듈 공개 인터페이스 |

## For AI Agents

### Working In This Directory
- `AudioManager`는 싱글톤 패턴 사용 - `get_audio_manager()`로 인스턴스 획득
- 오디오 파일 경로: `assets/audio/bg/` (BGM), `assets/audio/se/` (효과음), `assets/audio/me/` (음악 효과)
- PyInstaller 패키징 환경과 일반 실행 환경 모두 지원 (`sys._MEIPASS` 확인)
- 설정은 `src/core/config.py`의 `get_config()`로 읽음 (`audio.bgm.enabled`, `audio.master_volume` 등)
- BGM 전환 시 페이드 아웃/인 사용 (`fade_duration` 설정 가능)
- 오디오 비활성화 환경(CI 등)에서 pygame.mixer 초기화 실패를 graceful하게 처리

### Testing Requirements
- pytest tests 없음 - 오디오는 수동 테스트 필요
- 오디오 비활성화 상태에서 예외 없이 동작하는지 확인

### Common Patterns
```python
from src.audio.audio_manager import get_audio_manager
audio = get_audio_manager()
audio.play_bgm("town")        # BGM 재생
audio.play_sfx("attack")      # SFX 재생
audio.set_bgm_volume(0.5)     # 볼륨 조절
audio.stop_bgm(fade_out=True) # 페이드 아웃으로 정지
```

## Dependencies

### Internal
- `src.core.config` - 오디오 설정 읽기
- `src.core.logger` - 로깅

### External
- `pygame.mixer` - 오디오 재생 엔진

<!-- MANUAL: -->
