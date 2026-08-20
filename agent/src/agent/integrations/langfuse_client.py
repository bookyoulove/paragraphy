"""Langfuse observability/prompt-management client 초기화.

이 모듈을 import하는 시점에 `Langfuse(...)`를 한 번 생성해 두면, 이후 어디서든
`from langfuse import observe`(데코레이터)와 `get_client()`가 이 설정을 그대로
재사용한다 — Langfuse Python SDK(OTel 기반)는 프로세스 안에서 클라이언트를
전역으로 공유하는 구조이기 때문이다. 따라서 이 파일은 "클라이언트를 만드는
코드"가 아니라 "가장 먼저 한 번 구성해 두는" 진입점 역할을 한다.

키가 없는 로컬 개발 환경에서도 에이전트 자체는 죽지 않아야 하므로(가드레일과
동일한 fail-open 원칙), 설정이 없으면 `is_enabled=False`로 두고 트레이싱/프롬프트
조회 쪽에서 각자 조용히 우회하도록 한다.
"""

from __future__ import annotations

from functools import lru_cache

from langfuse import Langfuse, get_client

from agent.config import settings

is_enabled = bool(settings.langfuse_public_key and settings.langfuse_secret_key)

if is_enabled:
    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_base_url,
    )


@lru_cache(maxsize=1)
def get_langfuse_client() -> Langfuse | None:
    """구성된 Langfuse 클라이언트를 반환한다. 키가 없으면 None."""
    if not is_enabled:
        return None
    return get_client()