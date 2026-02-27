"""Alter - Claude LLMプロバイダー"""

from ai.provider_base import LLMProvider


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API プロバイダー"""

    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-latest"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            client = self._get_client()
            response = await client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=1024,
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            return f"[Claude エラー] {e}"

    def get_name(self) -> str:
        return "Claude"

    def is_configured(self) -> bool:
        return bool(self.api_key)
