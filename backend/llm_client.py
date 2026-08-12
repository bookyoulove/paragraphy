from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from .config import settings


class ClaudeClient:
    def __init__(self):
        self.client = Anthropic(api_key=settings.claude_api_key)
        self.model = "claude-2.1"

    async def complete(self, prompt: str, max_tokens: int = 1000):
        if not settings.claude_api_key:
            raise ValueError("Claude API key not configured")

        response = await self.client.completions.create(
            model=self.model,
            prompt=HUMAN_PROMPT + prompt + AI_PROMPT,
            max_tokens_to_sample=max_tokens,
            temperature=0.3,
        )
        if hasattr(response, "completion"):
            return response.completion
        return str(response)
