"""LangChain ChatModel 생성 경계.

에이전트는 OpenAI SDK나 특정 게이트웨이 SDK를 직접 호출하지 않는다.
``init_chat_model``에 OpenAI provider와 base URL을 주면 OpenAI-compatible
게이트웨이(OpenAI, 사내 프록시, LiteLLM 등)를 같은 방식으로 사용할 수 있다.

Langfuse observability: 여기서 반환하는 모델에 Langfuse의 LangChain
CallbackHandler를 미리 바인딩해 둔다(`with_config`). 그래프 노드들은 지금처럼
`model.invoke(...)`만 호출하면 되고, 그 프롬프트/응답/토큰 수/지연시간은 현재
활성화된 Langfuse trace/span에 자동으로 기록된다 — 호출부를 하나도 바꿀 필요가 없다.
"""

from __future__ import annotations

from functools import lru_cache
from typing import cast

from langchain.chat_models import init_chat_model
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from agent.config import settings
from agent.integrations.langfuse_client import is_enabled as langfuse_enabled


class LLMConfigurationError(RuntimeError):
    """모델을 초기화하기 위한 환경 설정이 부족할 때 발생한다."""


@lru_cache(maxsize=1)
def _langfuse_callbacks() -> list[BaseCallbackHandler]:
    if not langfuse_enabled:
        return []
    from langfuse.langchain import CallbackHandler

    return [CallbackHandler()]


@lru_cache(maxsize=1)
def _create_chat_model() -> BaseChatModel:
    """환경 설정으로 고정된 LangChain ChatModel을 생성한다."""
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


@lru_cache(maxsize=1)
def get_chat_model() -> Runnable[LanguageModelInput, AIMessage]:
    """환경 설정과 Langfuse 콜백이 적용된 ChatModel을 반환한다."""
    return _create_chat_model().with_config(callbacks=_langfuse_callbacks())


def get_structured_model[T: BaseModel](
    schema: type[T],
) -> Runnable[LanguageModelInput, T]:
    """주어진 Pydantic schema로 구조화 출력을 활성화한 모델을 반환한다.

    JSON을 시스템 프롬프트로 지시하거나 응답 텍스트를 직접 파싱하지 않는다.
    LangChain이 provider의 structured output 기능(JSON Schema/tool calling)을
    이용해 결과를 schema로 검증한다.

    주의: `with_structured_output()`은 내부적으로 새 Runnable을 구성하면서
    `get_chat_model()`에 이미 바인딩해 둔 callbacks 설정을 이어받지 않는다
    (실측 확인됨) — 그래서 여기서 다시 한번 `with_config`로 Langfuse 콜백을
    명시적으로 붙인다. 이 경로가 실제로 채점/첨삭/루브릭/가드레일 대부분이
    쓰는 경로라 빠뜨리면 LLM 호출 대부분이 트레이싱에서 누락된다.
    """
    structured = _create_chat_model().with_structured_output(schema)
    return cast(
        Runnable[LanguageModelInput, T],
        structured.with_config(callbacks=_langfuse_callbacks()),
    )
