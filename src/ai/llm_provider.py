"""
LLM 프로바이더 추상화 레이어

OpenAI와 Ollama를 동일한 인터페이스로 사용할 수 있도록
Protocol 기반 추상화를 제공합니다.
순환 임포트 방지를 위해 모든 임포트는 함수 내부에서 지연 로드합니다.
"""

from typing import Protocol, runtime_checkable, Optional, Any

from src.core.logger import get_logger

logger = get_logger("ai.llm_provider")


# =============================================================================
# 프로토콜 정의
# =============================================================================

@runtime_checkable
class LLMProvider(Protocol):
    """
    LLM 프로바이더 프로토콜

    이 프로토콜을 구현하면 OpenAI / Ollama / 임의의 백엔드를
    서로 교체하여 사용할 수 있습니다.
    """

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        텍스트 생성 요청

        Args:
            prompt: 사용자 입력 프롬프트
            system_prompt: 시스템 지시문 (선택)

        Returns:
            LLM이 생성한 응답 문자열
        """
        ...


# =============================================================================
# 구체 프로바이더 래퍼
# =============================================================================

class OpenAIProvider:
    """
    OpenAI 프로바이더

    OpenAIClientSync를 LLMProvider 인터페이스로 래핑합니다.
    """

    def __init__(self, client: Any):
        """
        Args:
            client: OpenAIClientSync 인스턴스
        """
        self._client = client

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """OpenAI API를 통해 텍스트 생성"""
        return self._client.generate(prompt, system_prompt)

    def get_usage_report(self) -> str:
        """토큰 사용량 리포트 (OpenAI 전용)"""
        if hasattr(self._client, "get_usage_report"):
            return self._client.get_usage_report()
        return "사용량 정보 없음"


class OllamaProvider:
    """
    Ollama 프로바이더

    OllamaClientSync를 LLMProvider 인터페이스로 래핑합니다.
    """

    def __init__(self, client: Any):
        """
        Args:
            client: OllamaClientSync 인스턴스
        """
        self._client = client

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Ollama 로컬 LLM을 통해 텍스트 생성"""
        return self._client.generate(prompt, system_prompt)


# =============================================================================
# 팩토리 함수
# =============================================================================

def create_provider(
    provider_type: str = "openai",
    **kwargs: Any,
) -> LLMProvider:
    """
    LLM 프로바이더 팩토리

    provider_type에 따라 적절한 프로바이더 인스턴스를 생성합니다.
    모든 임포트는 이 함수 내부에서 지연 로드하여 순환 임포트를 방지합니다.

    Args:
        provider_type: "openai" 또는 "ollama"
        **kwargs: 프로바이더별 설정 키워드 인수
            openai: api_key, model, temperature, max_tokens, json_mode, timeout,
                    retry_count, base_url
            ollama: base_url, model, use_cloud, temperature, timeout, max_tokens,
                    context_length, num_gpu, retry_count, enable_thinking,
                    play_style, enable_commentary, async_mode, detailed_prompt,
                    boss_mode

    Returns:
        LLMProvider 인터페이스를 구현한 프로바이더 인스턴스

    Raises:
        ValueError: 알 수 없는 provider_type인 경우
        ValueError: OpenAI API 키가 없는 경우

    Examples:
        >>> provider = create_provider("openai", api_key="sk-...")
        >>> provider = create_provider("ollama", model="llama3:8b")
    """
    provider_type = provider_type.lower().strip()

    if provider_type == "openai":
        # 지연 임포트: 순환 참조 방지
        from src.ai.openai_client import OpenAIConfig, OpenAIClientSync

        # kwargs에서 OpenAIConfig 필드만 추출
        config_fields = {
            "api_key", "model", "temperature", "max_tokens",
            "json_mode", "timeout", "retry_count", "base_url",
        }
        config_kwargs = {k: v for k, v in kwargs.items() if k in config_fields}
        config = OpenAIConfig(**config_kwargs)

        client = OpenAIClientSync(config)
        logger.info(f"OpenAI 프로바이더 생성: model={config.model}")
        return OpenAIProvider(client)

    elif provider_type == "ollama":
        # 지연 임포트: 순환 참조 방지
        from src.multiplayer.llm_player_bot import LLMConfig, OllamaClientSync, PlayStyle

        # kwargs에서 LLMConfig 필드만 추출
        config_fields = {
            "base_url", "model", "use_cloud", "temperature", "timeout",
            "max_tokens", "context_length", "num_gpu", "retry_count",
            "enable_thinking", "play_style", "enable_commentary",
            "async_mode", "detailed_prompt", "boss_mode",
        }
        config_kwargs = {k: v for k, v in kwargs.items() if k in config_fields}

        # play_style 문자열이면 Enum으로 변환
        if "play_style" in config_kwargs and isinstance(config_kwargs["play_style"], str):
            try:
                config_kwargs["play_style"] = PlayStyle(config_kwargs["play_style"])
            except ValueError:
                config_kwargs["play_style"] = PlayStyle.BALANCED

        config = LLMConfig(**config_kwargs)
        client = OllamaClientSync(config)
        logger.info(f"Ollama 프로바이더 생성: model={config.model}, base_url={config.base_url}")
        return OllamaProvider(client)

    else:
        raise ValueError(
            f"알 수 없는 provider_type: '{provider_type}'. "
            f"'openai' 또는 'ollama' 를 사용하세요."
        )


def create_provider_from_env() -> Optional[LLMProvider]:
    """
    환경변수에서 프로바이더 자동 감지 및 생성

    우선순위:
    1. OPENAI_API_KEY 환경변수가 있으면 OpenAI 프로바이더
    2. 없으면 Ollama 프로바이더 (로컬 기본값)
    3. 둘 다 실패하면 None 반환

    Returns:
        LLMProvider 인스턴스 또는 None (실패 시)
    """
    import os

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        try:
            provider = create_provider("openai", api_key=api_key)
            logger.info("환경변수에서 OpenAI 프로바이더 자동 생성")
            return provider
        except Exception as e:
            logger.warning(f"OpenAI 프로바이더 생성 실패, Ollama로 폴백: {e}")

    try:
        provider = create_provider("ollama")
        logger.info("Ollama 프로바이더 자동 생성 (로컬 기본값)")
        return provider
    except Exception as e:
        logger.error(f"Ollama 프로바이더 생성 실패: {e}")
        return None
