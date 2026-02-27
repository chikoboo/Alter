"""Alter - WebSocketルーター

FastAPIのWebSocketエンドポイントを定義。
Frontend (React) と Backend の双方向通信を管理する。
"""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import AppConfig
from audio.devices import list_audio_devices, AudioDevice
from audio.capture import AudioCapture
from transcription.engine import TranscriptionEngine, TranscriptSegment
from ai.thinking import ThinkingEngine
from ai.learning import UserUtterance
from session.manager import SessionManager

router = APIRouter()


class AlterBackend:
    """バックエンドの全機能を統合するクラス"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.session_manager = SessionManager(config.data_dir)
        self.thinking_engine = ThinkingEngine(config)
        self.transcription_engine = TranscriptionEngine(
            model_name=config.whisper_model,
            device=config.whisper_device,
            compute_type=config.whisper_compute_type,
            language=config.language,
            vad_threshold=config.vad_threshold,
            sample_rate=config.sample_rate,
        )
        self.audio_capture: Optional[AudioCapture] = None
        self._ws: Optional[WebSocket] = None
        self._transcription_task: Optional[asyncio.Task] = None

    async def send_message(self, msg: dict):
        """フロントエンドにメッセージを送信"""
        if self._ws:
            try:
                await self._ws.send_json(msg)
            except Exception:
                pass

    async def handle_message(self, data: dict):
        """フロントエンドからのメッセージを処理"""
        msg_type = data.get("type", "")

        if msg_type == "get_devices":
            await self._handle_get_devices()
        elif msg_type == "select_devices":
            await self._handle_select_devices(data)
        elif msg_type == "recording":
            await self._handle_recording(data)
        elif msg_type == "ai_request":
            await self._handle_ai_request(data)
        elif msg_type == "session_action":
            await self._handle_session_action(data)
        elif msg_type == "settings":
            await self._handle_settings(data)
        elif msg_type == "get_status":
            await self._send_status()
        elif msg_type == "get_sessions":
            await self._handle_get_sessions()

    # --- Handlers ---

    async def _handle_get_devices(self):
        devices = list_audio_devices()
        mics = [{"index": d.index, "name": d.name} for d in devices if d.is_input and not d.is_loopback]
        speakers = [{"index": d.index, "name": d.name} for d in devices if d.is_loopback]
        await self.send_message({
            "type": "devices",
            "microphones": mics,
            "speakers": speakers,
        })

    async def _handle_select_devices(self, data: dict):
        mic_id = data.get("mic_id")
        speaker_id = data.get("speaker_id")
        self.audio_capture = AudioCapture(
            mic_device_index=mic_id,
            speaker_device_index=speaker_id,
            sample_rate=self.config.sample_rate,
            chunk_duration=self.config.chunk_duration_sec,
        )
        await self.send_message({"type": "devices_selected", "success": True})

    async def _handle_recording(self, data: dict):
        action = data.get("action")

        if action == "start":
            if self.audio_capture is None:
                await self.send_message({"type": "error", "message": "デバイスが選択されていません"})
                return

            try:
                # セッションがなければ新規作成
                if self.session_manager.current_session is None:
                    self.session_manager.create_session()

                print("[DEBUG] 音声キャプチャ開始中...")
                self.audio_capture.start()
                print("[DEBUG] 音声キャプチャ開始成功")
                self._transcription_task = asyncio.create_task(self._transcription_loop())

                await self.send_message({
                    "type": "status",
                    "recording": True,
                    "session": self._session_info(),
                })
            except Exception as e:
                print(f"[ERROR] 録音開始エラー: {e}")
                import traceback
                traceback.print_exc()
                await self.send_message({"type": "error", "message": f"録音開始に失敗: {e}"})

        elif action == "stop":
            if self.audio_capture:
                self.audio_capture.stop()
            if self._transcription_task:
                self._transcription_task.cancel()
                self._transcription_task = None

            await self.send_message({"type": "status", "recording": False})

    async def _handle_ai_request(self, data: dict):
        selected_text = data.get("selected_text", "")
        context_lines = data.get("context_lines")

        if not selected_text:
            return

        await self.send_message({"type": "ai_loading", "loading": True})

        result = await self.thinking_engine.generate_response(
            selected_text=selected_text,
            transcript_log=self.session_manager.transcript_log,
            context_lines=context_lines,
        )

        # セッションに記録
        self.session_manager.add_ai_response(
            selected_text=selected_text,
            answer=result["answer"],
            provider=result["provider"],
        )

        await self.send_message({
            "type": "ai_response",
            "answer": result["answer"],
            "provider": result["provider"],
        })

    async def _handle_session_action(self, data: dict):
        action = data.get("action")

        if action == "new":
            name = data.get("name")
            session = self.session_manager.create_session(name)
            await self.send_message({
                "type": "session_info",
                **self._session_info(),
            })

        elif action == "switch":
            session_id = data.get("session_id", "")
            session = self.session_manager.load_session(session_id)
            if session:
                # 切り替えたセッションのログを送信
                await self.send_message({
                    "type": "session_loaded",
                    **self._session_info(),
                    "transcript_log": self.session_manager.transcript_log,
                })

        elif action == "rename":
            session_id = data.get("session_id", "")
            new_name = data.get("name", "")
            self.session_manager.rename_session(session_id, new_name)
            await self._handle_get_sessions()

    async def _handle_get_sessions(self):
        sessions = self.session_manager.list_sessions()
        await self.send_message({
            "type": "sessions_list",
            "sessions": [
                {"id": s.id, "name": s.name, "created_at": s.created_at}
                for s in sessions
            ],
        })

    async def _handle_settings(self, data: dict):
        provider = data.get("llm_provider")
        if provider:
            try:
                self.thinking_engine.set_provider(provider)
                await self.send_message({
                    "type": "settings_updated",
                    "llm_provider": provider,
                    "available_providers": self.thinking_engine.get_available_providers(),
                })
            except ValueError as e:
                await self.send_message({"type": "error", "message": str(e)})

    async def _send_status(self):
        await self.send_message({
            "type": "status",
            "recording": self.audio_capture is not None and self.audio_capture._running,
            "model_loaded": self.transcription_engine._model is not None,
            "llm_provider": self.config.llm_provider,
            "available_providers": self.thinking_engine.get_available_providers(),
            "session": self._session_info(),
        })

    # --- 文字起こしループ ---

    async def _transcription_loop(self):
        """音声チャンクを取得して文字起こしするループ"""
        loop = asyncio.get_event_loop()

        while True:
            try:
                # ブロッキングI/Oをスレッドプールで実行
                chunk = await loop.run_in_executor(None, self.audio_capture.get_chunk, 1.0)
                if chunk is None:
                    continue

                # 文字起こし（CPU/GPU処理なのでスレッドプールで実行）
                segment = await loop.run_in_executor(
                    None, self.transcription_engine.transcribe_chunk, chunk
                )
                if segment is None:
                    continue

                # セッションに記録
                self.session_manager.add_transcript(
                    speaker=segment.speaker,
                    text=segment.text,
                    timestamp=segment.timestamp,
                )

                # ユーザー発話を学習ストアに記録
                if segment.speaker == "you":
                    session_id = ""
                    if self.session_manager.current_session:
                        session_id = self.session_manager.current_session.id
                    self.thinking_engine.learning_store.record(UserUtterance(
                        text=segment.text,
                        timestamp=segment.timestamp,
                        session_id=session_id,
                    ))

                # フロントエンドに送信
                await self.send_message({
                    "type": "transcript",
                    "speaker": segment.speaker,
                    "text": segment.text,
                    "timestamp": segment.timestamp,
                })

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ERROR] 文字起こしループエラー: {e}")
                await asyncio.sleep(0.5)

    def _session_info(self) -> dict:
        s = self.session_manager.current_session
        if s:
            return {"id": s.id, "name": s.name, "created_at": s.created_at}
        return {}


# --- グローバルインスタンス ---
_backend: Optional[AlterBackend] = None


def init_backend(config: AppConfig) -> AlterBackend:
    global _backend
    _backend = AlterBackend(config)
    return _backend


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """メインWebSocketエンドポイント"""
    global _backend
    if _backend is None:
        print("[ERROR] _backend が初期化されていません")
        await ws.close()
        return

    await ws.accept()
    _backend._ws = ws
    print("[DEBUG] WebSocket接続完了、ステータス送信中...")

    # 接続時に初期ステータスを送信
    try:
        await _backend._send_status()
        print("[DEBUG] ステータス送信成功")
    except Exception as e:
        print(f"[ERROR] ステータス送信失敗: {e}")
        import traceback
        traceback.print_exc()

    try:
        while True:
            data = await ws.receive_json()
            print(f"[DEBUG] 受信: {data.get('type', 'unknown')}")
            await _backend.handle_message(data)
    except WebSocketDisconnect:
        print("[INFO] WebSocket切断")
    except Exception as e:
        print(f"[ERROR] WebSocketエラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        _backend._ws = None
