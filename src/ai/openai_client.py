"""
OpenAI API 클라이언트 - GPT-4o-mini 기반 게임 AI

Dawn of Stellar의 AI 의사결정을 위한 OpenAI API 동기 클라이언트.
OllamaClientSync와 동일한 인터페이스를 제공하여 쉽게 교체 가능합니다.
"""

import os
import time
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from src.core.logger import get_logger

logger = get_logger("ai.openai_client")


@dataclass
class OpenAIConfig:
    """OpenAI API 설정"""
    api_key: str = ""                           # env OPENAI_API_KEY
    model: str = "gpt-4o-mini"                 # 기본 모델 (비용 효율적)
    temperature: float = 0.3                    # 낮을수록 일관된 결정
    max_tokens: int = 512                       # 응답 토큰 수
    json_mode: bool = True                      # 구조화된 JSON 출력
    timeout: float = 30.0                       # 요청 타임아웃 (초)
    retry_count: int = 3                        # 재시도 횟수
    base_url: str = "https://api.openai.com/v1" # API 엔드포인트

    def __post_init__(self):
        """환경변수에서 API 키 자동 로드"""
        if not self.api_key:
            self.api_key = os.environ.get("OPENAI_API_KEY", "")


@dataclass
class TokenUsage:
    """토큰 사용량 및 비용 추적"""
    prompt_tokens: int = 0          # 입력 토큰 누계
    completion_tokens: int = 0      # 출력 토큰 누계
    total_tokens: int = 0           # 전체 토큰 누계
    total_cost: float = 0.0         # 추정 비용 (USD)
    request_count: int = 0          # 총 요청 횟수


class OpenAIClientSync:
    """
    동기 OpenAI 클라이언트 (게임 루프용)

    OllamaClientSync와 동일한 generate() 인터페이스를 제공합니다.
    지수 백오프를 사용한 자동 재시도를 지원합니다.
    """

    # GPT 모델별 가격 (1M 토큰당 USD)
    PRICING: Dict[str, Dict[str, float]] = {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o":      {"input": 2.50, "output": 10.0},
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    }

    def __init__(self, config: Optional[OpenAIConfig] = None):
        """
        Args:
            config: OpenAI 설정. None이면 기본값 사용 (환경변수에서 API 키 로드)
        """
        self.config = config or OpenAIConfig()
        self.usage = TokenUsage()

        if not self.config.api_key:
            raise ValueError(
                "OpenAI API 키가 필요합니다. "
                "OPENAI_API_KEY 환경변수를 설정하거나 OpenAIConfig(api_key=...) 로 전달하세요."
            )

        logger.info(f"OpenAIClientSync 초기화: model={self.config.model}, json_mode={self.config.json_mode}")

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        채팅 완성 API 호출

        지수 백오프(0.5초 → 1.0초 → 2.0초)로 자동 재시도합니다.

        Args:
            messages: [{"role": "system"|"user"|"assistant", "content": "..."}] 형식
            **kwargs: model, temperature, max_tokens 오버라이드 가능

        Returns:
            LLM 응답 문자열

        Raises:
            Exception: retry_count 초과 시
        """
        import httpx

        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model":       kwargs.get("model", self.config.model),
            "messages":    messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens":  kwargs.get("max_tokens", self.config.max_tokens),
        }

        # JSON 모드 활성화 시 구조화된 출력 강제
        if self.config.json_mode:
            payload["response_format"] = {"type": "json_object"}

        last_error: Optional[Exception] = None
        for attempt in range(self.config.retry_count):
            try:
                with httpx.Client(timeout=self.config.timeout) as client:
                    response = client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    result = response.json()

                # 토큰 사용량 추적
                self._track_usage(result.get("usage", {}))

                content = result["choices"][0]["message"]["content"]
                logger.debug(f"OpenAI 응답 (첫 100자): {content[:100]}...")
                return content

            except Exception as e:
                last_error = e
                wait_time = (2 ** attempt) * 0.5   # 0.5 → 1.0 → 2.0 초
                logger.warning(
                    f"OpenAI 요청 실패 (시도 {attempt + 1}/{self.config.retry_count}): {e}"
                )
                if attempt < self.config.retry_count - 1:
                    time.sleep(wait_time)

        logger.error(f"OpenAI 요청 최종 실패 (모든 재시도 소진): {last_error}")
        raise last_error  # type: ignore[misc]

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        generate 인터페이스 (OllamaClientSync 호환)

        OllamaClientSync.generate()와 동일한 시그니처로,
        llm_player_bot.py 코드를 수정 없이 사용할 수 있습니다.

        Args:
            prompt: 사용자 메시지
            system_prompt: 시스템 프롬프트 (선택)

        Returns:
            LLM 응답 문자열
        """
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages)

    def _track_usage(self, usage: Dict[str, int]) -> None:
        """토큰 사용량 및 추정 비용 누적"""
        prompt_tokens     = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        self.usage.prompt_tokens     += prompt_tokens
        self.usage.completion_tokens += completion_tokens
        self.usage.total_tokens      += prompt_tokens + completion_tokens
        self.usage.request_count     += 1

        # 알려진 모델 가격, 없으면 gpt-4o-mini 기준
        pricing = self.PRICING.get(self.config.model, self.PRICING["gpt-4o-mini"])
        cost = (
            prompt_tokens     * pricing["input"]  +
            completion_tokens * pricing["output"]
        ) / 1_000_000
        self.usage.total_cost += cost

    def get_usage_report(self) -> str:
        """사용량 요약 문자열 반환"""
        return (
            f"OpenAI 사용량: {self.usage.request_count}회 요청, "
            f"{self.usage.total_tokens:,} 토큰 "
            f"(입력: {self.usage.prompt_tokens:,}, 출력: {self.usage.completion_tokens:,}), "
            f"추정 비용: ${self.usage.total_cost:.4f}"
        )
