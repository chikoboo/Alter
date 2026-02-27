"""Alter - OpenAI LLMプロバイダー"""

from backend.ai.provider_base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI API プロバイダー"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=1024,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI エラー] {e}"

    def get_name(self) -> str:
        return "OpenAI"

    def is_configured(self) -> bool:
        return bool(self.api_key)
