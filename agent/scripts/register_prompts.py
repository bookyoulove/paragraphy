"""Langfuse에 에이전트 프롬프트를 한 번에 등록/갱신하는 1회성 스크립트.

`agent/src/agent/integrations/prompts.py`의 `PROMPT_TEMPLATES`(채점/첨삭/루브릭/
Tutor Chat 시스템 프롬프트)를 그대로 Langfuse Prompt Management에 업로드한다.
같은 이름으로 다시 실행하면 새 버전(version)이 하나 더 생기고 `production`
라벨이 그 최신 버전으로 옮겨진다 — 즉 재실행해도 안전하다(멱등하지는 않지만
누적 버전 관리가 Langfuse의 정상 동작이다).

실행:
    cd agent && uv run python scripts/register_prompts.py
    (또는 워크스페이스 루트에서: uv run --package agent python agent/scripts/register_prompts.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent.integrations.langfuse_client import get_langfuse_client
from agent.integrations.prompts import PROMPT_TEMPLATES


def main() -> None:
    client = get_langfuse_client()
    if client is None:
        raise SystemExit(
            "LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY가 설정되지 않았습니다. "
            "프로젝트 루트 .env를 확인하세요."
        )

    for name, template in PROMPT_TEMPLATES.items():
        prompt = client.create_prompt(
            name=name,
            prompt=template,
            type="text",
            labels=["production"],
            tags=["paragraphy", "agent"],
        )
        print(f"[ok] {name} -> version {prompt.version}")

    client.flush()
    print(f"\n완료: {len(PROMPT_TEMPLATES)}개 프롬프트 등록/갱신")


if __name__ == "__main__":
    main()