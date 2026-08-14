"""LangChain ChatModel 생성 경계.

에이전트는 OpenAI SDK나 특정 게이트웨이 SDK를 직접 호출하지 않는다.
``init_chat_model``에 OpenAI provider와 base URL을 주면 OpenAI-compatible
게이트웨이(OpenAI, 사내 프록시, LiteLLM 등)를 같은 방식으로 사용할 수 있다.
"""

from __future__ import annotations

from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from agent.config import settings


class LLMConfigurationError(RuntimeError):
    """모델을 초기화하기 위한 환경 설정이 부족할 때 발생한다."""


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    """환경 설정으로 고정된 LangChain ChatModel을 반환한다."""
    if not settings.ai_cloud_api_key:
        raise LLMConfigurationError(
            "AI_CLOUD_API_KEY 또는 OPENAI_API_KEY가 설정되지 않았습니다. .env를 확인하세요."
        )
    if not settings.ai_cloud_base_url:
        raise LLMConfigurationError(
            "AI_CLOUD_BASE_URL 또는 OPENAI_BASE_URL이 설정되지 않았습니다."
        )

    return init_chat_model(
        model=settings.ai_cloud_model,
        model_provider="openai",
        api_key=settings.ai_cloud_api_key,
        base_url=settings.ai_cloud_base_url,
    )


def get_structured_model[T: BaseModel](
    schema: type[T],
) -> Runnable[LanguageModelInput, T]:
    """주어진 Pydantic schema로 구조화 출력을 활성화한 모델을 반환한다.

    JSON을 시스템 프롬프트로 지시하거나 응답 텍스트를 직접 파싱하지 않는다.
    LangChain이 provider의 structured output 기능(JSON Schema/tool calling)을
    이용해 결과를 schema로 검증한다.
    """
    return get_chat_model().with_structured_output(schema)  # type: ignore
