"""에이전트 노드들이 공유하는 유틸 (JSON 응답 파싱 등)."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json(text: str) -> dict[str, Any]:
    """LLM 응답에서 JSON 객체를 최대한 관대하게 추출한다."""
    text = text.strip()
    # ```json ... ``` 코드펜스 제거
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 앞뒤에 잡문이 섞인 경우 첫 '{'부터 마지막 '}'까지만 재시도
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("응답에서 JSON 객체를 찾을 수 없습니다.")
