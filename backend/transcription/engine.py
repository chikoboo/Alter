"""Alter - 文字起こしエンジン

faster-whisperを使用したリアルタイム音声文字起こし。
音声チャンクを受け取り、話者タグ付きのテキストを生成する。
"""

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from audio.capture import AudioChunk
from transcription.vad import VoiceActivityDetector


@dataclass
class TranscriptSegment:
    """文字起こし結果の1セグメント"""
    speaker: str  # "you" or "target"
    text: str
    timestamp: float
    duration: float


class TranscriptionEngine:
    """faster-whisperベースの文字起こしエンジン"""

    def __init__(
        self,
        model_name: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16",
        language: str = "ja",
        vad_threshold: float = 0.5,
        sample_rate: int = 16000,
    ):
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.sample_rate = sample_rate
        self._model = None
        self._vad = VoiceActivityDetector(threshold=vad_threshold, sample_rate=sample_rate)
        self._on_transcript: Optional[Callable[[TranscriptSegment], None]] = None
        self._running = False
        self._lock = threading.Lock()

        # CUDA利用可能チェック（警告のみ）
        if self.device == "cuda":
            self._check_cuda_available()

    @staticmethod
    def _check_cuda_available() -> bool:
        """CUDAが実際に利用可能かチェック"""
        # 1. ctranslate2でCUDAデバイスを確認
        try:
            import ctranslate2
            if hasattr(ctranslate2, 'get_cuda_device_count'):
                count = ctranslate2.get_cuda_device_count()
                if count == 0:
                    print("[INFO] CUDAデバイスが見つかりません")
                    return False
                print(f"[INFO] CUDAデバイス検出: {count}台")
            else:
                # get_cuda_device_countがない古いバージョン
                pass
        except Exception as e:
            print(f"[INFO] ctranslate2 CUDAチェック失敗: {e}")
            return False

        # 2. cuBLAS DLLの存在確認（Windows）
        import sys
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.CDLL("cublas64_12.dll")
                print("[INFO] cublas64_12.dll 検出済み")
            except OSError:
                print("[INFO] cublas64_12.dll が見つかりません")
                return False

        return True

    def load_model(self):
        """Whisperモデルを読み込む（初回のみ）"""
        if self._model is not None:
            return

        print(f"[INFO] faster-whisper モデル '{self.model_name}' を読み込み中... (device={self.device}, compute={self.compute_type})")
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
            print(f"[INFO] モデル読み込み完了 (device={self.device})")
        except Exception as e:
            print(f"[ERROR] モデル読み込みに失敗: {e}")
            # CPUフォールバック
            if self.device == "cuda":
                self._fallback_to_cpu()

    def _fallback_to_cpu(self):
        """CUDA失敗時にCPUモデルに切り替える"""
        print("[INFO] CPUにフォールバックします...")
        self.device = "cpu"
        self.compute_type = "int8"
        self._model = None
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8",
            )
            print("[INFO] CPUモデル読み込み完了")
        except Exception as e:
            print(f"[ERROR] CPUフォールバックも失敗: {e}")
            self._model = None

    def set_callback(self, callback: Callable[[TranscriptSegment], None]):
        """文字起こし結果のコールバックを設定する"""
        self._on_transcript = callback

    def transcribe_chunk(self, chunk: AudioChunk) -> Optional[TranscriptSegment]:
        """音声チャンクを文字起こしする

        Args:
            chunk: 音声チャンク（source, data, timestamp）

        Returns:
            文字起こし結果。無音の場合はNone。
        """
        # VADで発話区間をチェック
        if not self._vad.contains_speech(chunk.data):
            return None

        # モデルが読み込まれていなければ読み込む
        self.load_model()
        if self._model is None:
            return None

        try:
            with self._lock:
                segments, info = self._model.transcribe(
                    chunk.data,
                    language=self.language,
                    beam_size=3,  # スピード優先でやや小さめ
                    vad_filter=False,  # 自前VAD使用のため無効
                    without_timestamps=True,
                )

                # セグメントを結合
                texts = []
                for seg in segments:
                    text = seg.text.strip()
                    if text:
                        texts.append(text)

                if not texts:
                    return None

                full_text = " ".join(texts)

                result = TranscriptSegment(
                    speaker=chunk.source,
                    text=full_text,
                    timestamp=chunk.timestamp,
                    duration=len(chunk.data) / self.sample_rate,
                )

                # コールバックを呼ぶ
                if self._on_transcript:
                    self._on_transcript(result)

                return result

        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] 文字起こしエラー: {error_msg}")

            # CUDA/cuBLAS系エラーの場合、CPUにフォールバック
            if "cublas" in error_msg.lower() or "cuda" in error_msg.lower():
                self._fallback_to_cpu()

            return None
