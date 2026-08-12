import httpx
from .config import settings


class ClaudeClient:
    def __init__(self):
        self.base_url = settings.claude_api_url
        self.api_key = settings.claude_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def complete(self, prompt: str, max_tokens: int = 1000):
        if not self.api_key or not self.base_url:
            raise ValueError("Claude API URL or key not configured")

        payload = {
            "model": "claude-2.1",  # default fallback
            "prompt": prompt,
            "max_tokens_to_sample": max_tokens,
            "temperature": 0.3,
            "top_p": 1.0,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()

        if "completion" in data:
            return data["completion"]
        if "output" in data and isinstance(data["output"], str):
            return data["output"]
        if "completion" in data and isinstance(data["completion"], dict):
            return data["completion"].get("content", "")
        return str(data)
