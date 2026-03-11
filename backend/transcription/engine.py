"""Alter - 文字起こしエンジン

moonshine-voiceを使用したリアルタイム音声文字起こし。
音声チャンクを受け取り、イベントベースでテキストを生成する。
マイクとスピーカーの2ソースを個別のStreamで管理する。
"""

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from audio.capture import AudioChunk


@dataclass
class TranscriptSegment:
    """文字起こし結果の1セグメント"""
    speaker: str  # "you" or "target"
    text: str
    timestamp: float
    duration: float


class TranscriptionEngine:
    """Moonshine Voiceベースの文字起こしエンジン

    1つのTranscriberに対して、マイク用・スピーカー用の2つのStreamを作成し、
    それぞれの音声を独立して文字起こしする。
    結果はイベントリスナー経由でコールバックされる。
    """

    def __init__(
        self,
        language: str = "ja",
        model_path: str = "",
        model_arch: int = 0,
        vad_threshold: float = 0.5,
        sample_rate: int = 16000,
    ):
        self.language = language
        self._model_path = model_path
        self._model_arch = model_arch
        self._vad_threshold = vad_threshold
        self.sample_rate = sample_rate
        self._transcriber = None
        self._mic_stream = None
        self._speaker_stream = None
        self._on_transcript: Optional[Callable[[TranscriptSegment], None]] = None
        self._running = False
        self._lock = threading.Lock()

    def load_model(self):
        """Moonshineモデルを読み込む（初回のみ）"""
        if self._transcriber is not None:
            return

        print(f"[INFO] Moonshine Voice モデルを読み込み中... (language={self.language})")
        try:
            from moonshine_voice import Transcriber, TranscriptEventListener

            # モデルが指定されていなければ自動ダウンロード
            if not self._model_path:
                print(f"[INFO] モデルをダウンロード中 (language={self.language})...")
                result = self._download_model()
                if result:
                    self._model_path = result.model_path
                    self._model_arch = result.model_arch
                    print(f"[INFO] モデルダウンロード完了: {self._model_path} (arch={self._model_arch})")
                else:
                    print("[ERROR] モデルのダウンロードに失敗しました")
                    return

            # 日本語等の非ラテン言語向けオプション
            options = {
                "vad_threshold": str(self._vad_threshold),
                "return_audio_data": "false",  # メモリ節約
            }
            # 非ラテン言語ではトークン数上限を緩和
            if self.language not in ("en", "es"):
                options["max_tokens_per_second"] = "13.0"

            self._transcriber = Transcriber(
                model_path=self._model_path,
                model_arch=self._model_arch,
                options=options,
            )

            print(f"[INFO] Moonshine Voice モデル読み込み完了")
        except Exception as e:
            print(f"[ERROR] Moonshine Voice モデル読み込みに失敗: {e}")
            import traceback
            traceback.print_exc()
            self._transcriber = None

    def _download_model(self):
        """CLIツールでモデルをダウンロードし、パスとアーキテクチャを返す。"""
        import subprocess
        import sys

        class _DownloadResult:
            def __init__(self, model_path, model_arch):
                self.model_path = model_path
                self.model_arch = model_arch

        print(f"[INFO] python -m moonshine_voice.download --language {self.language} を実行中...")

        try:
            result = subprocess.run(
                [sys.executable, "-m", "moonshine_voice.download", "--language", self.language],
                capture_output=True,
                text=True,
                timeout=300,  # ダウンロードに最大5分
            )

            output = result.stdout + result.stderr
            print(output)

            # CLIの出力からパスとアーキテクチャを抽出
            # 例: "Downloaded model path: /path/to/model"
            # 例: "Model arch: 1"
            model_path = ""
            model_arch = 0

            for line in output.splitlines():
                line = line.strip()
                if "Downloaded model path:" in line:
                    model_path = line.split("Downloaded model path:", 1)[1].strip()
                elif "Model arch:" in line:
                    try:
                        model_arch = int(line.split("Model arch:", 1)[1].strip())
                    except ValueError:
                        pass

            if model_path:
                return _DownloadResult(model_path, model_arch)
            else:
                print(f"[ERROR] モデルパスを取得できませんでした。CLIの出力:\n{output}")
                return None

        except subprocess.TimeoutExpired:
            print("[ERROR] ダウンロードがタイムアウトしました")
            return None
        except Exception as e:
            print(f"[ERROR] ダウンロードコマンド実行エラー: {e}")
            return None



    @property
    def model_loaded(self) -> bool:
        """モデルが読み込まれているかどうか"""
        return self._transcriber is not None

    def set_callback(self, callback: Callable[[TranscriptSegment], None]):
        """文字起こし結果のコールバックを設定する"""
        self._on_transcript = callback

    def start(self):
        """文字起こしセッションを開始する

        マイク用・スピーカー用の2つのStreamを作成しリスナーを登録する。
        """
        self.load_model()
        if self._transcriber is None:
            print("[ERROR] モデルが読み込まれていないため開始できません")
            return

        try:
            from moonshine_voice import TranscriptEventListener

            # マイク用Stream
            self._mic_stream = self._transcriber.create_stream(flags=0)
            mic_listener = _StreamListener(self, "you")
            self._mic_stream.add_listener(mic_listener)
            self._mic_stream.start()

            # スピーカー用Stream
            self._speaker_stream = self._transcriber.create_stream(flags=0)
            speaker_listener = _StreamListener(self, "target")
            self._speaker_stream.add_listener(speaker_listener)
            self._speaker_stream.start()

            self._running = True
            print("[INFO] Moonshine Voice 文字起こしセッション開始")
        except Exception as e:
            print(f"[ERROR] 文字起こしセッション開始エラー: {e}")
            import traceback
            traceback.print_exc()

    def stop(self):
        """文字起こしセッションを停止する"""
        self._running = False
        try:
            if self._mic_stream:
                self._mic_stream.stop()
                self._mic_stream = None
            if self._speaker_stream:
                self._speaker_stream.stop()
                self._speaker_stream = None
        except Exception as e:
            print(f"[WARNING] セッション停止エラー: {e}")

    def feed_audio(self, chunk: AudioChunk):
        """音声チャンクを対応するStreamに送る

        Args:
            chunk: 音声チャンク（source, data, timestamp）
        """
        if not self._running:
            return

        try:
            stream = self._mic_stream if chunk.source == "you" else self._speaker_stream
            if stream is None:
                return

            # numpy配列をリストとして渡す
            stream.add_audio(chunk.data.tolist(), self.sample_rate)
        except Exception as e:
            print(f"[WARNING] 音声フィードエラー ({chunk.source}): {e}")

    def _handle_line_completed(self, speaker: str, text: str, start_time: float, duration: float):
        """Streamリスナーから完了行を受け取るコールバック"""
        if not text or not text.strip():
            return

        segment = TranscriptSegment(
            speaker=speaker,
            text=text.strip(),
            timestamp=time.time(),
            duration=duration,
        )

        if self._on_transcript:
            self._on_transcript(segment)


class _StreamListener:
    """Moonshineの文字起こしイベントリスナー

    on_line_completed が呼ばれたときに TranscriptionEngine のコールバックを呼ぶ。
    on_line_text_changed でリアルタイムの中間結果も処理可能（将来拡張用）。
    """

    def __init__(self, engine: TranscriptionEngine, speaker: str):
        self._engine = engine
        self._speaker = speaker

    def on_line_started(self, event):
        """行の開始（ログ用）"""
        pass

    def on_line_text_changed(self, event):
        """テキスト更新（将来的にリアルタイムプレビューに使用可能）"""
        pass

    def on_line_completed(self, event):
        """行の完了 — 確定テキストをエンジンに通知"""
        line = event.line
        self._engine._handle_line_completed(
            speaker=self._speaker,
            text=line.text,
            start_time=line.start_time,
            duration=line.duration,
        )

    def on_line_updated(self, event):
        """行の更新（テキスト以外の変更含む）"""
        pass
