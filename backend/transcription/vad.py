"""Alter - VAD（音声区間検出）

Silero VADを使用して音声チャンクから発話区間を検出する。
無音チャンクをフィルタリングし、文字起こしエンジンの負荷を軽減する。
"""

import numpy as np


class VoiceActivityDetector:
    """Silero VADを使った音声区間検出"""

    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self._model = None
        self._utils = None

    def _load_model(self):
        """VADモデルを遅延読み込みする"""
        if self._model is not None:
            return

        try:
            import torch
            self._model, self._utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                trust_repo=True,
            )
        except Exception as e:
            print(f"[WARNING] Silero VAD の読み込みに失敗しました: {e}")
            print("[WARNING] VADなしで続行します（全チャンクを処理）")

    def contains_speech(self, audio: np.ndarray) -> bool:
        """音声チャンク内に発話が含まれるかを判定する

        Args:
            audio: float32 モノラル音声データ (16kHz)

        Returns:
            発話が含まれる場合 True
        """
        self._load_model()

        if self._model is None:
            # VADが使えない場合は常にTrueを返す
            return True

        try:
            import torch

            # numpy → torch tensor
            tensor = torch.from_numpy(audio).float()

            # Silero VADは512サンプル単位で処理
            # チャンク全体をスキャンして、どこかに発話があればTrue
            window_size = 512
            for i in range(0, len(tensor) - window_size, window_size):
                window = tensor[i : i + window_size]
                confidence = self._model(window, self.sample_rate).item()
                if confidence > self.threshold:
                    return True

            return False

        except Exception as e:
            print(f"[WARNING] VAD処理エラー: {e}")
            return True  # エラー時は安全側（処理する）

    def reset(self):
        """VADの内部状態をリセットする"""
        if self._model is not None:
            self._model.reset_states()
