import json
import re
from openai import AsyncOpenAI
from .config import settings


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(raw[start : end + 1])
    raise ValueError(f"LLM 응답에서 JSON을 파싱할 수 없습니다: {raw[:200]}")


class ClaudeClient:
    """Paragraphy 채점/첨삭/튜터 에이전트가 공용으로 쓰는 LLM 클라이언트.

    이 환경에서는 Anthropic Claude가 OpenAI 호환 엔드포인트(claude-fable-5)로
    프록시되어 있어 openai SDK로 접속한다.
    """

    def __init__(self):
        if not settings.claude_api_key:
            raise ValueError("CLAUDE_FABLE5_API_KEY가 설정되지 않았습니다.")
        base_url = settings.claude_api_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        self.client = AsyncOpenAI(base_url=base_url, api_key=settings.claude_api_key)
        self.model = "claude-fable-5"

    async def complete_json(self, system: str, user: str, max_tokens: int = 2000) -> dict:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        last_error = None
        for attempt in range(2):
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
            )
            raw = response.choices[0].message.content or ""
            try:
                return _extract_json(raw)
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                messages = messages + [
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": (
                            "방금 응답이 유효한 JSON이 아니었습니다 (파싱 오류: "
                            f"{exc}). 문자열 값 내부에는 큰따옴표(\") 대신 작은따옴표나 「」를 사용하고, "
                            "다른 설명이나 코드펜스 없이 유효한 JSON 객체 하나만 다시 출력하세요."
                        ),
                    },
                ]
        raise ValueError(f"LLM이 유효한 JSON을 반환하지 못했습니다: {last_error}")

    async def chat(self, messages: list, tools: list | None = None, max_tokens: int = 800):
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
        )
        return response.choices[0].message
