"""Alter Backend - アプリケーション設定管理"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class AppConfig:
    """アプリケーション設定"""

    # --- オーディオ ---
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_sec: float = 2.0  # 音声チャンクの長さ（秒）

    # --- 文字起こし ---
    whisper_model: str = "large-v3"
    whisper_device: str = "cuda"
    whisper_compute_type: str = ""  # auto: cuda→float16, cpu→int8
    language: str = "ja"
    vad_threshold: float = 0.5

    # --- LLM ---
    llm_provider: Literal["gemini", "openai", "claude"] = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    openai_model: str = "gpt-4o-mini"
    claude_model: str = "claude-3-5-haiku-latest"

    # --- コンテキスト ---
    max_context_lines: int = 30
    few_shot_examples: int = 5

    # --- セッション ---
    data_dir: Path = field(default_factory=lambda: Path("data"))

    # --- サーバー ---
    host: str = "127.0.0.1"
    port: int = 8765

    def __post_init__(self):
        """環境変数からAPIキーを読み込む"""
        self.gemini_api_key = self.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.openai_api_key = self.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        self.anthropic_api_key = self.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")

        # compute_type を自動設定
        if not self.whisper_compute_type:
            self.whisper_compute_type = "float16" if self.whisper_device == "cuda" else "int8"

        # dataディレクトリを作成
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "sessions").mkdir(exist_ok=True)
        (self.data_dir / "user_profile").mkdir(exist_ok=True)

    @property
    def active_api_key(self) -> str:
        """現在選択中のプロバイダーのAPIキーを返す"""
        keys = {
            "gemini": self.gemini_api_key,
            "openai": self.openai_api_key,
            "claude": self.anthropic_api_key,
        }
        return keys.get(self.llm_provider, "")

    @property
    def active_model(self) -> str:
        """現在選択中のプロバイダーのモデル名を返す"""
        models = {
            "gemini": self.gemini_model,
            "openai": self.openai_model,
            "claude": self.claude_model,
        }
        return models.get(self.llm_provider, "")
