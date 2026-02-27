"""Alter - セッション管理

会議ごとにデータを分離して保存・復元する。
文字起こしログ、AI回答履歴、メタ情報をセッション単位で管理する。
"""

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class SessionMetadata:
    """セッションメタ情報"""
    id: str
    name: str
    created_at: str
    updated_at: str
    mic_device: str = ""
    speaker_device: str = ""


class SessionManager:
    """セッションの作成・保存・復元・切替"""

    def __init__(self, data_dir: Path):
        self.sessions_dir = data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._current_session: Optional[SessionMetadata] = None
        self._transcript_log: list[dict] = []

    @property
    def current_session(self) -> Optional[SessionMetadata]:
        return self._current_session

    @property
    def transcript_log(self) -> list[dict]:
        return self._transcript_log

    def create_session(self, name: Optional[str] = None) -> SessionMetadata:
        """新しいセッションを作成する"""
        now = datetime.now()
        session_id = now.strftime("%Y-%m-%d_%H%M%S")
        session_name = name or now.strftime("%m/%d %H:%M 会議")

        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        metadata = SessionMetadata(
            id=session_id,
            name=session_name,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
        )

        self._save_metadata(metadata)
        self._current_session = metadata
        self._transcript_log = []

        return metadata

    def load_session(self, session_id: str) -> Optional[SessionMetadata]:
        """既存セッションを読み込む"""
        session_dir = self.sessions_dir / session_id
        metadata_path = session_dir / "metadata.json"

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            metadata = SessionMetadata(**data)
            self._current_session = metadata

            # ログを読み込む
            self._transcript_log = self._load_transcript(session_id)

            return metadata
        except Exception as e:
            print(f"[ERROR] セッション読み込みエラー: {e}")
            return None

    def load_latest_session(self) -> Optional[SessionMetadata]:
        """最新のセッションを読み込む"""
        sessions = self.list_sessions()
        if not sessions:
            return None
        return self.load_session(sessions[0].id)

    def list_sessions(self) -> list[SessionMetadata]:
        """全セッション一覧を返す（新しい順）"""
        sessions = []
        for session_dir in sorted(self.sessions_dir.iterdir(), reverse=True):
            if not session_dir.is_dir():
                continue
            metadata_path = session_dir / "metadata.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    sessions.append(SessionMetadata(**data))
                except Exception:
                    continue
        return sessions

    def add_transcript(self, speaker: str, text: str, timestamp: float):
        """文字起こし結果をセッションに追加する"""
        entry = {
            "speaker": speaker,
            "text": text,
            "timestamp": timestamp,
        }
        self._transcript_log.append(entry)

        # ファイルに追記
        if self._current_session:
            self._append_to_log("transcript.jsonl", entry)
            self._update_timestamp()

    def add_ai_response(self, selected_text: str, answer: str, provider: str):
        """AI回答をセッションに記録する"""
        entry = {
            "selected_text": selected_text,
            "answer": answer,
            "provider": provider,
            "timestamp": time.time(),
        }

        if self._current_session:
            self._append_to_log("ai_responses.jsonl", entry)

    def rename_session(self, session_id: str, new_name: str):
        """セッション名を変更する"""
        metadata_path = self.sessions_dir / session_id / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["name"] = new_name
            data["updated_at"] = datetime.now().isoformat()
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if self._current_session and self._current_session.id == session_id:
                self._current_session.name = new_name

    # --- Private ---

    def _save_metadata(self, metadata: SessionMetadata):
        session_dir = self.sessions_dir / metadata.id
        metadata_path = session_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(asdict(metadata), f, ensure_ascii=False, indent=2)

    def _append_to_log(self, filename: str, entry: dict):
        if not self._current_session:
            return
        log_path = self.sessions_dir / self._current_session.id / filename
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _load_transcript(self, session_id: str) -> list[dict]:
        log_path = self.sessions_dir / session_id / "transcript.jsonl"
        if not log_path.exists():
            return []
        entries = []
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def _update_timestamp(self):
        if self._current_session:
            self._current_session.updated_at = datetime.now().isoformat()
            self._save_metadata(self._current_session)
