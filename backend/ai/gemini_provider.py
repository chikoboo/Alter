"""Alter - Gemini LLMプロバイダー"""

from ai.provider_base import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini API プロバイダー"""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            client = self._get_client()
            response = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config={
                    "system_instruction": system_prompt,
                    "temperature": 0.7,
                    "max_output_tokens": 1024,
                },
            )
            return response.text or ""
        except Exception as e:
            return f"[Gemini エラー] {e}"

    def get_name(self) -> str:
        return "Gemini"

    def is_configured(self) -> bool:
        return bool(self.api_key)
