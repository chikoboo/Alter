"""Alter - オーディオキャプチャ

マイク入力とスピーカー出力（WASAPIループバック）を同時にキャプチャする。
各ソースからの音声チャンクをキューに送出し、文字起こしエンジンに供給する。
"""

import sys
import threading
import time
import queue
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class AudioChunk:
    """音声チャンクデータ"""
    source: str  # "you" or "target"
    data: np.ndarray  # float32, mono, 16kHz
    timestamp: float  # Unix timestamp


class AudioCapture:
    """マイクとスピーカーの同時音声キャプチャ"""

    def __init__(
        self,
        mic_device_index: Optional[int] = None,
        speaker_device_index: Optional[int] = None,
        sample_rate: int = 16000,
        chunk_duration: float = 2.0,
    ):
        self.mic_device_index = mic_device_index
        self.speaker_device_index = speaker_device_index
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_size = int(sample_rate * chunk_duration)

        self.audio_queue: queue.Queue[AudioChunk] = queue.Queue()
        self._running = False
        self._mic_thread: Optional[threading.Thread] = None
        self._speaker_thread: Optional[threading.Thread] = None

    def start(self):
        """キャプチャを開始する"""
        if self._running:
            return

        self._running = True

        if sys.platform == "win32":
            self._start_windows_capture()
        else:
            self._start_dummy_capture()

    def stop(self):
        """キャプチャを停止する"""
        self._running = False
        if self._mic_thread:
            self._mic_thread.join(timeout=3.0)
        if self._speaker_thread:
            self._speaker_thread.join(timeout=3.0)

    def get_chunk(self, timeout: float = 1.0) -> Optional[AudioChunk]:
        """キューから次の音声チャンクを取得する"""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    # --- Windows (WASAPI) ---

    def _start_windows_capture(self):
        """Windows WASAPI経由のキャプチャスレッドを起動"""
        if self.mic_device_index is not None:
            self._mic_thread = threading.Thread(
                target=self._capture_mic_windows,
                daemon=True,
                name="mic-capture",
            )
            self._mic_thread.start()

        if self.speaker_device_index is not None:
            self._speaker_thread = threading.Thread(
                target=self._capture_speaker_windows,
                daemon=True,
                name="speaker-capture",
            )
            self._speaker_thread.start()

    def _capture_mic_windows(self):
        """マイク入力スレッド（Windows）"""
        try:
            import pyaudiowpatch as pyaudio  # type: ignore
        except ImportError:
            print("[ERROR] pyaudiowpatch が見つかりません")
            return

        p = pyaudio.PyAudio()
        try:
            dev_info = p.get_device_info_by_index(self.mic_device_index)
            native_rate = int(dev_info.get("defaultSampleRate", self.sample_rate))
            channels = min(dev_info.get("maxInputChannels", 1), 2)
            frames_per_buffer = int(native_rate * 0.1)  # 100ms バッファ

            stream = p.open(
                format=pyaudio.paFloat32,
                channels=channels,
                rate=native_rate,
                input=True,
                input_device_index=self.mic_device_index,
                frames_per_buffer=frames_per_buffer,
            )

            self._read_stream(stream, "you", native_rate, channels)
            stream.stop_stream()
            stream.close()
        except Exception as e:
            print(f"[ERROR] マイクキャプチャエラー: {e}")
        finally:
            p.terminate()

    def _capture_speaker_windows(self):
        """スピーカー出力ループバックスレッド（Windows）"""
        try:
            import pyaudiowpatch as pyaudio  # type: ignore
        except ImportError:
            print("[ERROR] pyaudiowpatch が見つかりません")
            return

        p = pyaudio.PyAudio()
        try:
            dev_info = p.get_device_info_by_index(self.speaker_device_index)
            native_rate = int(dev_info.get("defaultSampleRate", self.sample_rate))
            channels = min(dev_info.get("maxInputChannels", 2), 2)
            frames_per_buffer = int(native_rate * 0.1)

            stream = p.open(
                format=pyaudio.paFloat32,
                channels=channels,
                rate=native_rate,
                input=True,
                input_device_index=self.speaker_device_index,
                frames_per_buffer=frames_per_buffer,
            )

            self._read_stream(stream, "target", native_rate, channels)
            stream.stop_stream()
            stream.close()
        except Exception as e:
            print(f"[ERROR] スピーカーキャプチャエラー: {e}")
        finally:
            p.terminate()

    def _read_stream(self, stream, source: str, native_rate: int, channels: int):
        """ストリームから音声を読み取り、リサンプル後にキューに投入"""
        buffer = np.array([], dtype=np.float32)
        target_chunk_samples = int(self.sample_rate * self.chunk_duration)

        while self._running:
            try:
                frames_per_read = int(native_rate * 0.1)
                raw = stream.read(frames_per_read, exception_on_overflow=False)
                audio = np.frombuffer(raw, dtype=np.float32)

                # ステレオ → モノラルに変換
                if channels > 1:
                    audio = audio.reshape(-1, channels).mean(axis=1)

                # リサンプリング（必要な場合）
                if native_rate != self.sample_rate:
                    ratio = self.sample_rate / native_rate
                    new_length = int(len(audio) * ratio)
                    indices = np.linspace(0, len(audio) - 1, new_length)
                    audio = np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

                buffer = np.concatenate([buffer, audio])

                # バッファが十分溜まったらチャンクを送出
                while len(buffer) >= target_chunk_samples:
                    chunk_data = buffer[:target_chunk_samples]
                    buffer = buffer[target_chunk_samples:]
                    self.audio_queue.put(AudioChunk(
                        source=source,
                        data=chunk_data,
                        timestamp=time.time(),
                    ))

            except Exception as e:
                if self._running:
                    print(f"[WARNING] ストリーム読み取りエラー ({source}): {e}")
                    time.sleep(0.1)

    # --- ダミー（開発環境用）---

    def _start_dummy_capture(self):
        """Linux開発環境用のダミーキャプチャ"""
        self._mic_thread = threading.Thread(
            target=self._dummy_stream,
            args=("you",),
            daemon=True,
            name="dummy-mic",
        )
        self._speaker_thread = threading.Thread(
            target=self._dummy_stream,
            args=("target",),
            daemon=True,
            name="dummy-speaker",
        )
        self._mic_thread.start()
        self._speaker_thread.start()

    def _dummy_stream(self, source: str):
        """ダミー音声を生成（無音）"""
        while self._running:
            silence = np.zeros(self.chunk_size, dtype=np.float32)
            self.audio_queue.put(AudioChunk(
                source=source,
                data=silence,
                timestamp=time.time(),
            ))
            time.sleep(self.chunk_duration)
