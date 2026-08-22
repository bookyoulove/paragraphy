"""외부 호출에 공통으로 적용하는 제한적 재시도 정책."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Iterator

from tenacity import (
    AsyncRetrying,
    RetryCallState,
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = {408, 409, 429}
_RETRYABLE_GRPC_CODES = {
    "ABORTED",
    "DEADLINE_EXCEEDED",
    "RESOURCE_EXHAUSTED",
    "UNAVAILABLE",
}
_RETRYABLE_EXCEPTION_PARTS = (
    "connection",
    "incompletejson",
    "internalserver",
    "jsondecode",
    "outputparser",
    "ratelimit",
    "serviceunavailable",
    "timeout",
    "temporarilyunavailable",
    "validationerror",
)


class StructuredOutputError(RuntimeError):
    """LLM 응답은 왔지만 구조화 출력 계약을 만족하지 못한 경우."""


def _exception_chain(exc: BaseException) -> Iterator[BaseException]:
    """래핑된 SDK 예외까지 검사한다."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _status_code(exc: BaseException) -> int | None:
    status_code = getattr(exc, "status_code", None)
    if status_code is None:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
    return status_code if isinstance(status_code, int) else None


def _grpc_code_name(exc: BaseException) -> str:
    code = getattr(exc, "code", None)
    if not callable(code):
        return ""
    try:
        value = code()
    except Exception:
        return ""
    name = getattr(value, "name", None)
    return str(name or value).upper()


def is_retryable_error(exc: BaseException) -> bool:
    """일시적인 외부 장애와 재생성 가능한 structured output만 허용한다."""
    for error in _exception_chain(exc):
        status_code = _status_code(error)
        if status_code in _RETRYABLE_STATUS_CODES or (
            status_code is not None and status_code >= 500
        ):
            return True

        if _grpc_code_name(error) in _RETRYABLE_GRPC_CODES:
            return True

        if isinstance(error, StructuredOutputError):
            return True

        if isinstance(error, (ConnectionError, TimeoutError)):
            return True

        exception_name = type(error).__name__.lower()
        if any(part in exception_name for part in _RETRYABLE_EXCEPTION_PARTS):
            return True

    return False


def _log_retry(operation_name: str, retry_state: RetryCallState) -> None:
    outcome = retry_state.outcome
    exception = outcome.exception() if outcome and outcome.failed else None
    logger.warning(
        "%s failed on attempt %d; retrying in %.2fs: %s",
        operation_name,
        retry_state.attempt_number,
        retry_state.idle_for,
        exception,
    )


def retrying(
    operation_name: str,
    *,
    max_attempts: int = 3,
    max_wait: float = 8.0,
) -> Retrying:
    """동기 외부 호출용 bounded exponential-backoff 정책을 반환한다."""
    return Retrying(
        retry=retry_if_exception(is_retryable_error),
        stop=stop_after_attempt(max_attempts),
        wait=wait_random_exponential(multiplier=1, max=max_wait),
        before_sleep=lambda state: _log_retry(operation_name, state),
        reraise=True,
    )


def call_with_retry[T](
    operation: Callable[[], T],
    *,
    operation_name: str,
    max_attempts: int = 3,
    max_wait: float = 8.0,
) -> T:
    """일시적인 오류만 재시도하고 최종 예외는 호출자에게 전달한다."""
    return retrying(
        operation_name,
        max_attempts=max_attempts,
        max_wait=max_wait,
    )(operation)


def invoke_with_retry[T](
    invoke: Callable[[str], T],
    base_prompt: str,
    *,
    operation_name: str,
    max_attempts: int = 3,
    max_wait: float = 8.0,
) -> T:
    """구조화 LLM 호출을 재시도하며 이전 오류를 다음 prompt에 전달한다."""
    attempt_number = 0
    last_error = ""

    def operation() -> T:
        nonlocal attempt_number, last_error
        attempt_number += 1
        prompt = base_prompt
        if attempt_number > 1:
            prompt += (
                f"\n\n이전 구조화 출력이 실패했다. 오류: {last_error}. 다시 시도하라."
            )
        try:
            return invoke(prompt)
        except Exception as exc:
            last_error = str(exc)
            raise

    return call_with_retry(
        operation,
        operation_name=operation_name,
        max_attempts=max_attempts,
        max_wait=max_wait,
    )


async def ainvoke_with_retry[T](
    invoke: Callable[[str], Awaitable[T]],
    base_prompt: str,
    *,
    operation_name: str,
    max_attempts: int = 3,
    max_wait: float = 8.0,
) -> T:
    """비동기 구조화 LLM 호출을 재시도하며 이전 오류를 다음 prompt에 전달한다."""
    attempt_number = 0
    last_error = ""

    async def operation() -> T:
        nonlocal attempt_number, last_error
        attempt_number += 1
        prompt = base_prompt
        if attempt_number > 1:
            prompt += (
                f"\n\n이전 구조화 출력이 실패했다. 오류: {last_error}. 다시 시도하라."
            )
        try:
            return await invoke(prompt)
        except Exception as exc:
            last_error = str(exc)
            raise

    retry = AsyncRetrying(
        retry=retry_if_exception(is_retryable_error),
        stop=stop_after_attempt(max_attempts),
        wait=wait_random_exponential(multiplier=1, max=max_wait),
        before_sleep=lambda state: _log_retry(operation_name, state),
        reraise=True,
    )
    return await retry(operation)
