"""Alter - LLMプロバイダー抽象基底クラス

Strategyパターンで複数のLLMプロバイダー（Gemini, OpenAI, Claude）を
統一インターフェースで切り替え可能にする。
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """LLMプロバイダーの抽象基底クラス"""

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """回答を生成する

        Args:
            system_prompt: システムプロンプト（役割・制約の定義）
            user_prompt: ユーザープロンプト（コンテキスト + 質問）

        Returns:
            生成されたテキスト
        """
        ...

    @abstractmethod
    def get_name(self) -> str:
        """プロバイダー名を返す"""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """APIキーが設定済みかを返す"""
        ...
