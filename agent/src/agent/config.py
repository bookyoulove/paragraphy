"""에이전트 패키지의 환경 설정.

실제 모델 SDK나 FastAPI 설정을 그래프 코드에서 직접 참조하지 않도록 한다.
OpenAI 호환 게이트웨이를 사용하므로 provider는 항상 ``openai``로 고정한다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# 실행 위치에 따라 .env를 찾지 못하는 일을 줄인다. 값은 환경 변수가 우선한다.
load_dotenv()
_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PACKAGE_ROOT / ".env")
load_dotenv(_PACKAGE_ROOT.parent / ".env")


@dataclass(frozen=True, slots=True)
class AgentSettings:
    ai_cloud_api_key: str | None
    ai_cloud_base_url: str | None
    ai_cloud_model: str
    ai_cloud_grading_temperature: float | None
    ai_cloud_grading_replicas: int
    langfuse_public_key: str | None
    langfuse_secret_key: str | None
    langfuse_base_url: str | None


def _supports_custom_temperature(model_name: str) -> bool:
    """현재 게이트웨이에서 확인된 temperature 지원 모델인지 판단한다."""
    return "gemini-3.1" in model_name.lower()


def _grading_temperature(model_name: str) -> float | None:
    default = "0.8" if _supports_custom_temperature(model_name) else ""
    raw = os.getenv("AI_CLOUD_GRADING_TEMPERATURE", default).strip()
    if not raw:
        return None
    try:
        temperature = float(raw)
    except ValueError as exc:
        raise ValueError(
            "AI_CLOUD_GRADING_TEMPERATURE은 숫자이거나 비워 두어야 합니다."
        ) from exc
    if not 0 <= temperature <= 2:
        raise ValueError("AI_CLOUD_GRADING_TEMPERATURE은 0과 2 사이여야 합니다.")
    return temperature


def _grading_replicas() -> int:
    raw = os.getenv("AI_CLOUD_GRADING_REPLICAS", "3").strip()
    try:
        replicas = int(raw)
    except ValueError as exc:
        raise ValueError("AI_CLOUD_GRADING_REPLICAS는 정수여야 합니다.") from exc
    if replicas < 1:
        raise ValueError("AI_CLOUD_GRADING_REPLICAS는 1 이상이어야 합니다.")
    return replicas


_model_name = (
    os.getenv("AI_CLOUD_MODEL")
    or os.getenv("OPENAI_MODEL")
    or os.getenv("MODEL_NAME")
    or os.getenv("RUBRIC_MODEL_NAME")
    or "anthropic/claude-sonnet-5"
)


settings = AgentSettings(
    ai_cloud_api_key=os.getenv("AI_CLOUD_API_KEY") or os.getenv("OPENAI_API_KEY"),
    ai_cloud_base_url=(
        os.getenv("AI_CLOUD_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("BASE_URL")
    ),
    ai_cloud_model=_model_name,
    ai_cloud_grading_temperature=_grading_temperature(_model_name),
    ai_cloud_grading_replicas=_grading_replicas(),
    langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    langfuse_base_url=os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST"),
)
