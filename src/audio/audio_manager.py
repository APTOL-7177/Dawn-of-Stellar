"""
Audio Manager - 오디오 시스템

pygame.mixer를 사용한 BGM 및 SFX 재생 관리
"""

import pygame.mixer
from pathlib import Path
from typing import Optional, Dict
from src.core.config import get_config
from src.core.logger import get_logger


class AudioManager:
    """
    오디오 매니저

    BGM(배경음악)과 SFX(효과음)를 관리합니다.
    """

    def __init__(self):
        """오디오 매니저 초기화"""
        self.logger = get_logger("audio")
        self.config = get_config()

        # 오디오 활성화 여부
        self.bgm_enabled = self.config.get("audio.bgm.enabled", True)
        self.sfx_enabled = self.config.get("audio.sfx.enabled", True)

        # 볼륨 설정
        self.master_volume = self.config.get("audio.master_volume", 0.8)
        self.bgm_volume = self.config.get("audio.bgm_volume", 0.6)
        self.sfx_volume = self.config.get("audio.sfx_volume", 0.7)

        # 페이드 설정
        self.fade_duration = self.config.get("audio.bgm.fade_duration", 1.0)

        # 현재 재생 중인 BGM
        self.current_bgm: Optional[str] = None

        # SFX 캐시 (자주 사용하는 SFX를 메모리에 보관)
        self.sfx_cache: Dict[str, pygame.mixer.Sound] = {}

        # 오디오 경로
        self.bgm_dir = Path("assets/audio/bgm")
        self.sfx_dir = Path("assets/audio/sfx")

        # pygame.mixer 초기화
        self._initialize_mixer()

    def _initialize_mixer(self) -> None:
        """pygame.mixer 초기화"""
        try:
            # 고품질 오디오 설정
            pygame.mixer.init(
                frequency=44100,  # 44.1kHz
                size=-16,         # 16-bit signed
                channels=2,       # 스테레오
                buffer=512        # 버퍼 크기 (낮을수록 지연 시간 감소)
            )

            # 동시 재생 가능한 SFX 채널 수
            pygame.mixer.set_num_channels(16)

            self.logger.info("pygame.mixer 초기화 완료")

        except Exception as e:
            self.logger.error(f"pygame.mixer 초기화 실패: {e}")
            self.bgm_enabled = False
            self.sfx_enabled = False

    def play_bgm(self, track_name: str, loop: bool = True, fade_in: bool = True) -> bool:
        """
        BGM 재생

        Args:
            track_name: config.yaml에 정의된 트랙 이름 (예: "main_menu")
            loop: 반복 재생 여부
            fade_in: 페이드 인 사용 여부

        Returns:
            재생 성공 여부
        """
        if not self.bgm_enabled:
            return False

        # 이미 같은 BGM이 재생 중이면 무시
        if self.current_bgm == track_name:
            return True

        # config에서 파일명 가져오기
        file_name = self.config.get(f"audio.bgm.tracks.{track_name}")
        if not file_name:
            self.logger.warning(f"BGM 트랙 '{track_name}'이 config.yaml에 정의되지 않음")
            return False

        # 파일 경로 찾기 (여러 확장자 시도)
        file_path = self._find_audio_file(self.bgm_dir, file_name)
        if not file_path:
            self.logger.warning(f"BGM 파일 '{file_name}'을 찾을 수 없음")
            return False

        try:
            # 현재 BGM 페이드 아웃 및 정지
            if pygame.mixer.music.get_busy():
                fade_ms = int(self.fade_duration * 1000)
                pygame.mixer.music.fadeout(fade_ms)
                # fadeout이 완료될 때까지 잠시 대기 (비차단)
                pygame.time.wait(min(100, fade_ms // 2))

            # 새 BGM 로드
            pygame.mixer.music.load(str(file_path))

            # 볼륨 설정
            volume = self.master_volume * self.bgm_volume
            pygame.mixer.music.set_volume(volume)

            # 재생
            loops = -1 if loop else 0
            if fade_in:
                fade_ms = int(self.fade_duration * 1000)
                pygame.mixer.music.play(loops, fade_ms=fade_ms)
            else:
                pygame.mixer.music.play(loops)

            self.current_bgm = track_name
            self.logger.info(f"BGM 재생: {track_name} ({file_path.name})")
            return True

        except Exception as e:
            self.logger.error(f"BGM 재생 실패 ({track_name}): {e}")
            return False

    def stop_bgm(self, fade_out: bool = True) -> None:
        """
        BGM 정지

        Args:
            fade_out: 페이드 아웃 사용 여부
        """
        if not pygame.mixer.music.get_busy():
            return

        try:
            if fade_out:
                fade_ms = int(self.fade_duration * 1000)
                pygame.mixer.music.fadeout(fade_ms)
            else:
                pygame.mixer.music.stop()

            self.current_bgm = None
            self.logger.info("BGM 정지")

        except Exception as e:
            self.logger.error(f"BGM 정지 실패: {e}")

    def pause_bgm(self) -> None:
        """BGM 일시정지"""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.logger.debug("BGM 일시정지")

    def resume_bgm(self) -> None:
        """BGM 재개"""
        pygame.mixer.music.unpause()
        self.logger.debug("BGM 재개")

    def play_sfx(self, category: str, sfx_name: str, volume_multiplier: float = 1.0) -> bool:
        """
        SFX 재생

        Args:
            category: SFX 카테고리 (ui, combat, character, skill, item, world)
            sfx_name: config.yaml에 정의된 SFX 이름
            volume_multiplier: 볼륨 배율 (기본 1.0)

        Returns:
            재생 성공 여부
        """
        if not self.sfx_enabled:
            return False

        # config에서 파일명 가져오기
        file_name = self.config.get(f"audio.sfx.{category}.{sfx_name}")
        if not file_name:
            self.logger.debug(f"SFX '{category}.{sfx_name}'이 config.yaml에 정의되지 않음")
            return False

        # 캐시 확인
        cache_key = f"{category}.{sfx_name}"
        if cache_key in self.sfx_cache:
            sound = self.sfx_cache[cache_key]
        else:
            # 파일 경로 찾기 (sfx 디렉토리 바로 아래)
            file_path = self._find_audio_file(self.sfx_dir, file_name)
            if not file_path:
                self.logger.debug(f"SFX 파일 '{file_name}'을 찾을 수 없음")
                return False

            try:
                # SFX 로드
                sound = pygame.mixer.Sound(str(file_path))
                self.sfx_cache[cache_key] = sound

            except Exception as e:
                self.logger.error(f"SFX 로드 실패 ({cache_key}): {e}")
                return False

        try:
            # 볼륨 설정 및 재생
            volume = self.master_volume * self.sfx_volume * volume_multiplier
            sound.set_volume(volume)
            sound.play()

            self.logger.debug(f"SFX 재생: {cache_key}")
            return True

        except Exception as e:
            self.logger.error(f"SFX 재생 실패 ({cache_key}): {e}")
            return False

    def _find_audio_file(self, directory: Path, file_name: str) -> Optional[Path]:
        """
        오디오 파일 찾기 (여러 확장자 시도)

        Args:
            directory: 검색 디렉토리
            file_name: 파일명 (확장자 포함 또는 미포함)

        Returns:
            파일 경로 또는 None
        """
        if not directory.exists():
            return None

        # 확장자가 이미 있는 경우
        if Path(file_name).suffix:
            file_path = directory / file_name
            if file_path.exists():
                return file_path
            return None

        # 여러 확장자 시도
        extensions = [".ogg", ".mp3", ".wav", ".flac", ".m4a"]
        for ext in extensions:
            file_path = directory / f"{file_name}{ext}"
            if file_path.exists():
                return file_path

        return None

    def set_master_volume(self, volume: float) -> None:
        """
        마스터 볼륨 설정

        Args:
            volume: 볼륨 (0.0 ~ 1.0)
        """
        self.master_volume = max(0.0, min(1.0, volume))
        self._update_volumes()

    def set_bgm_volume(self, volume: float) -> None:
        """
        BGM 볼륨 설정

        Args:
            volume: 볼륨 (0.0 ~ 1.0)
        """
        self.bgm_volume = max(0.0, min(1.0, volume))
        self._update_volumes()

    def set_sfx_volume(self, volume: float) -> None:
        """
        SFX 볼륨 설정

        Args:
            volume: 볼륨 (0.0 ~ 1.0)
        """
        self.sfx_volume = max(0.0, min(1.0, volume))

    def _update_volumes(self) -> None:
        """현재 재생 중인 오디오의 볼륨 업데이트"""
        if pygame.mixer.music.get_busy():
            volume = self.master_volume * self.bgm_volume
            pygame.mixer.music.set_volume(volume)

    def cleanup(self) -> None:
        """오디오 시스템 정리"""
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            self.sfx_cache.clear()
            self.logger.info("오디오 시스템 종료")
        except Exception as e:
            self.logger.error(f"오디오 시스템 종료 실패: {e}")


# 전역 인스턴스
_audio_manager: Optional[AudioManager] = None


def get_audio_manager() -> AudioManager:
    """전역 오디오 매니저 인스턴스"""
    global _audio_manager
    if _audio_manager is None:
        _audio_manager = AudioManager()
    return _audio_manager


def play_bgm(track_name: str, loop: bool = True, fade_in: bool = True) -> bool:
    """
    BGM 재생 (편의 함수)

    Args:
        track_name: 트랙 이름
        loop: 반복 재생
        fade_in: 페이드 인

    Returns:
        재생 성공 여부
    """
    return get_audio_manager().play_bgm(track_name, loop, fade_in)


def stop_bgm(fade_out: bool = True) -> None:
    """
    BGM 정지 (편의 함수)

    Args:
        fade_out: 페이드 아웃
    """
    get_audio_manager().stop_bgm(fade_out)


def play_sfx(category: str, sfx_name: str, volume_multiplier: float = 1.0) -> bool:
    """
    SFX 재생 (편의 함수)

    Args:
        category: 카테고리
        sfx_name: SFX 이름
        volume_multiplier: 볼륨 배율

    Returns:
        재생 성공 여부
    """
    return get_audio_manager().play_sfx(category, sfx_name, volume_multiplier)
