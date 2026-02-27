"""Alter - シンキングエンジン（回答生成オーケストレーター）

コンテキスト構築 → LLMプロバイダー呼び出し → 回答返却の
パイプラインを統合管理する。
"""

from typing import Optional

from ai.provider_base import LLMProvider
from ai.gemini_provider import GeminiProvider
from ai.openai_provider import OpenAIProvider
from ai.claude_provider import ClaudeProvider
from ai.context import ContextBuilder
from ai.learning import LearningStore
from config import AppConfig


class ThinkingEngine:
    """AI回答生成エンジン"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.learning_store = LearningStore(config.data_dir)
        self.context_builder = ContextBuilder(
            self.learning_store,
            max_context_lines=config.max_context_lines,
        )

        # プロバイダーを初期化
        self._providers: dict[str, LLMProvider] = {
            "gemini": GeminiProvider(config.gemini_api_key, config.gemini_model),
            "openai": OpenAIProvider(config.openai_api_key, config.openai_model),
            "claude": ClaudeProvider(config.anthropic_api_key, config.claude_model),
        }

    @property
    def current_provider(self) -> LLMProvider:
        """現在選択中のLLMプロバイダーを返す"""
        return self._providers[self.config.llm_provider]

    def get_available_providers(self) -> list[str]:
        """APIキーが設定済みのプロバイダー名リストを返す"""
        return [name for name, p in self._providers.items() if p.is_configured()]

    def set_provider(self, provider_name: str):
        """LLMプロバイダーを切り替える"""
        if provider_name in self._providers:
            self.config.llm_provider = provider_name
        else:
            raise ValueError(f"不明なプロバイダー: {provider_name}")

    async def generate_response(
        self,
        selected_text: str,
        transcript_log: list[dict],
        context_lines: Optional[int] = None,
    ) -> dict:
        """選択テキストに対するAI回答を生成する

        Args:
            selected_text: ユーザーが選択したテキスト
            transcript_log: 文字起こしログ
            context_lines: 使用するコンテキスト行数

        Returns:
            {"answer": str, "provider": str}
        """
        provider = self.current_provider

        if not provider.is_configured():
            return {
                "answer": f"[エラー] {provider.get_name()} のAPIキーが設定されていません。",
                "provider": provider.get_name(),
            }

        # コンテキスト構築
        payload = self.context_builder.build(
            selected_text=selected_text,
            transcript_log=transcript_log,
            context_lines=context_lines,
        )

        # LLM呼び出し
        answer = await provider.generate(payload.system_prompt, payload.user_prompt)

        return {
            "answer": answer,
            "provider": provider.get_name(),
        }
