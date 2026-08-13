"""학교 AI Cloud LLM 게이트웨이 연동 서비스.

OpenAI 호환 API(`POST /v1/chat/completions`)를 제공하는 사내 게이트웨이를
`openai` 파이썬 라이브러리로 호출한다. base_url/api_key만 게이트웨이로 바꿔
꽂은 것이므로, 실제 백엔드 모델은 Anthropic Claude(`anthropic/claude-sonnet-5`)다.

Rubric/Grading/Chatting 에이전트가 전부 이 모듈의 `chat_completion()` 하나만
호출하도록 한다 (spelling_service.py와 동일한 원칙: 클라이언트 생성 등 SDK
세부사항은 이 파일 안에 캡슐화).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.core.config import settings

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("paragraphy.llm_gateway")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(LOG_DIR / "llm_gateway.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(file_handler)
    logger.propagate = True  # 콘솔(uvicorn 로그)에도 같이 뜨게 둔다


class LLMClientError(RuntimeError):
    """AI Cloud 게이트웨이 호출 실패 시 발생."""


@lru_cache(maxsize=1)
def _get_client() -> OpenAI:
    if not settings.ai_cloud_api_key:
        raise LLMClientError(
            "AI_CLOUD_API_KEY가 설정되지 않았습니다. 프로젝트 루트 .env를 확인하세요."
        )
    return OpenAI(api_key=settings.ai_cloud_api_key, base_url=settings.ai_cloud_base_url)


def chat_completion(
    messages: list[ChatCompletionMessageParam],
    *,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float | None = None,
) -> str:
    """messages를 AI Cloud 게이트웨이로 보내고 assistant 응답 텍스트를 반환한다.

    Args:
        messages: OpenAI Chat Completions 형식 메시지 목록.
        model: 미지정 시 settings.ai_cloud_model(anthropic/claude-sonnet-5) 사용.
        max_tokens: 응답 최대 토큰 수.
        temperature: 게이트웨이 뒷단 모델(Claude)이 이 파라미터를 지원하지 않는
            경우(400 "temperature is deprecated for this model")가 있어 기본값은
            아예 보내지 않음(None). 필요할 때만 명시적으로 넘긴다.

    Raises:
        LLMClientError: API 키 미설정 또는 호출 실패 시.
    """
    client = _get_client()
    kwargs = {"model": model or settings.ai_cloud_model, "messages": messages, "max_tokens": max_tokens}
    if temperature is not None:
        kwargs["temperature"] = temperature
    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:  # openai SDK 예외를 서비스 레이어 예외로 통일
        logger.error("게이트웨이 호출 자체 실패: %s | model=%s max_tokens=%s", exc, kwargs["model"], max_tokens)
        raise LLMClientError(f"AI Cloud 게이트웨이 호출 실패: {exc}") from exc

    choice = response.choices[0]
    content = choice.message.content

    if content is None:
        # content가 비는 경우의 원인 후보: finish_reason(length/content_filter 등),
        # refusal 필드(모더레이션 거부), 게이트웨이가 content 대신 다른 필드에
        # 응답을 실었을 가능성 등 — 재현 시 원인 파악을 위해 원본 응답을 통째로 남긴다.
        try:
            raw_dump = response.model_dump_json(indent=2)
        except Exception:
            raw_dump = repr(response)
        logger.error(
            "content=None 응답 수신. finish_reason=%s refusal=%s model=%s max_tokens=%s\n원본 응답:\n%s",
            getattr(choice, "finish_reason", None),
            getattr(choice.message, "refusal", None),
            kwargs["model"],
            max_tokens,
            raw_dump,
        )
        refusal = getattr(choice.message, "refusal", None)
        detail = f"finish_reason={getattr(choice, 'finish_reason', None)}"
        if refusal:
            detail += f", refusal={refusal!r}"
        raise LLMClientError(
            f"AI Cloud 게이트웨이 응답에 content가 없습니다 ({detail}). "
            f"원본 응답은 backend/logs/llm_gateway.log에 기록했습니다."
        )
    return content


if __name__ == "__main__":
    # 스모크 테스트: 실제 게이트웨이로 샘플 메시지 하나가 정상 응답하는지 확인.
    reply = chat_completion(
        [
            {
                "role": "user",
                "content": (
                    "너는 대입 논술 채점 보조 AI다. 연결 테스트다. "
                    "정확히 한 문장으로, 네가 논술 채점/첨삭을 도울 준비가 되었다고 한국어로 답해라."
                ),
            }
        ]
    )
    print("=== 모델 ===")
    print(settings.ai_cloud_model)
    print("=== 응답 ===")
    print(reply)
