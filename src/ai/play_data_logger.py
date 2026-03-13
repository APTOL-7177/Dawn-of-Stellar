"""
플레이 데이터 로거 - 행동 복제(Behavioral Cloning)용 데이터 수집

전투 및 탐험 행동을 JSONL 형식으로 기록하여
추후 모델 학습 또는 분석에 활용합니다.

파일 형식: data/play_logs/{episode_id}.jsonl
각 줄: {"episode_id": ..., "turn": ..., "timestamp": ..., "state": ..., "action": ..., "reward": ..., "done": ...}
"""

import json
import time
import threading
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from src.core.logger import get_logger

logger = get_logger("ai.play_data_logger")


class PlayDataLogger:
    """
    플레이 데이터 JSONL 로거

    에피소드 단위로 플레이 데이터를 기록합니다.
    스레드 안전(thread-safe) 구현으로 멀티플레이어 환경에서도 사용 가능합니다.

    사용 예:
        logger = PlayDataLogger()
        ep_id = logger.start_episode()
        logger.log_step(state_dict, action_dict, reward=0.1, done=False)
        logger.end_episode(result="win")
    """

    def __init__(self, log_dir: str = "data/play_logs"):
        """
        Args:
            log_dir: 로그 파일을 저장할 디렉터리 (없으면 자동 생성)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 현재 에피소드 상태
        self._episode_id: Optional[str] = None
        self._turn: int = 0
        self._file = None           # 열린 파일 핸들
        self._lock = threading.Lock()  # 스레드 안전 잠금

        logger.info(f"PlayDataLogger 초기화: log_dir={self.log_dir.resolve()}")

    # -------------------------------------------------------------------------
    # 에피소드 관리
    # -------------------------------------------------------------------------

    def start_episode(self, episode_id: Optional[str] = None) -> str:
        """
        새 에피소드 시작

        이전 에피소드가 열려 있으면 자동으로 종료합니다.

        Args:
            episode_id: 에피소드 ID. None이면 UUID 자동 생성

        Returns:
            사용된 episode_id 문자열
        """
        with self._lock:
            # 이전 에피소드 자동 종료
            if self._file is not None:
                self._close_file()

            self._episode_id = episode_id or str(uuid.uuid4())
            self._turn = 0

            log_path = self.log_dir / f"{self._episode_id}.jsonl"
            self._file = open(log_path, "w", encoding="utf-8")

            logger.debug(f"에피소드 시작: {self._episode_id} -> {log_path}")
            return self._episode_id

    def end_episode(self, result: str = "unknown") -> None:
        """
        에피소드 종료 및 요약 기록

        Args:
            result: 결과 문자열 ("win", "lose", "timeout", "flee" 등)
        """
        with self._lock:
            if self._file is None:
                logger.warning("end_episode 호출 시 열린 에피소드가 없습니다.")
                return

            # 에피소드 요약 레코드 기록
            summary = {
                "episode_id": self._episode_id,
                "type":       "episode_summary",
                "total_turns": self._turn,
                "result":     result,
                "timestamp":  time.time(),
            }
            # _close_file() 호출 전에 값 저장 (_close_file이 None으로 초기화함)
            finished_id = self._episode_id
            finished_turns = self._turn

            self._write_line(summary)
            self._close_file()

            logger.info(
                f"에피소드 종료: {finished_id}, "
                f"총 {finished_turns}턴, 결과={result}"
            )

    # -------------------------------------------------------------------------
    # 스텝 기록
    # -------------------------------------------------------------------------

    def log_step(
        self,
        state: Dict[str, Any],
        action: Dict[str, Any],
        reward: float,
        done: bool,
    ) -> None:
        """
        단일 스텝(상태-행동-보상) 기록

        Args:
            state:  현재 게임 상태 딕셔너리
            action: 수행한 행동 딕셔너리
            reward: 이 스텝의 보상값
            done:   에피소드 종료 여부
        """
        with self._lock:
            if self._file is None:
                logger.warning("log_step 호출 시 열린 에피소드가 없습니다. start_episode()를 먼저 호출하세요.")
                return

            self._turn += 1
            record = {
                "episode_id": self._episode_id,
                "turn":       self._turn,
                "timestamp":  time.time(),
                "state":      state,
                "action":     action,
                "reward":     reward,
                "done":       done,
            }
            self._write_line(record)

    # -------------------------------------------------------------------------
    # 보상 계산
    # -------------------------------------------------------------------------

    @staticmethod
    def calculate_step_reward(events: Dict[str, Any]) -> float:
        """
        게임 이벤트에서 스텝 보상 계산

        보상 체계:
          - 적 처치:    +1.0
          - 아군 사망:  -1.0
          - BREAK 성공: +0.1
          - 데미지 딜:  damage_dealt / 1000.0

        Args:
            events: 이번 스텝에서 발생한 이벤트 딕셔너리
                가능한 키:
                    kill (bool)          - 적 처치 여부
                    ally_death (bool)    - 아군 사망 여부
                    break_success (bool) - BREAK 성공 여부
                    damage_dealt (int)   - 가한 데미지

        Returns:
            계산된 보상 실수값
        """
        reward = 0.0

        if events.get("kill", False):
            reward += 1.0

        if events.get("ally_death", False):
            reward -= 1.0

        if events.get("break_success", False):
            reward += 0.1

        damage = events.get("damage_dealt", 0)
        if damage > 0:
            reward += damage / 1000.0

        return round(reward, 6)

    # -------------------------------------------------------------------------
    # 내부 헬퍼
    # -------------------------------------------------------------------------

    def _write_line(self, record: Dict[str, Any]) -> None:
        """JSONL 한 줄 기록 (잠금 없이 호출 — 반드시 _lock 보유 상태에서 사용)"""
        try:
            line = json.dumps(record, ensure_ascii=False, default=str)
            self._file.write(line + "\n")
            self._file.flush()
        except Exception as e:
            logger.error(f"JSONL 기록 실패: {e}")

    def _close_file(self) -> None:
        """파일 닫기 (잠금 없이 호출 — 반드시 _lock 보유 상태에서 사용)"""
        try:
            if self._file:
                self._file.close()
        except Exception as e:
            logger.error(f"파일 닫기 실패: {e}")
        finally:
            self._file = None
            self._episode_id = None
            self._turn = 0

    def __del__(self):
        """소멸자: 열린 파일 안전하게 닫기"""
        with self._lock:
            if self._file is not None:
                self._close_file()

    # -------------------------------------------------------------------------
    # 프로퍼티
    # -------------------------------------------------------------------------

    @property
    def is_recording(self) -> bool:
        """현재 에피소드 기록 중 여부"""
        return self._file is not None

    @property
    def current_episode_id(self) -> Optional[str]:
        """현재 에피소드 ID (없으면 None)"""
        return self._episode_id

    @property
    def current_turn(self) -> int:
        """현재 에피소드의 턴 수"""
        return self._turn
