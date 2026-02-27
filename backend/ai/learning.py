"""Alter - 学習ループ（Few-shot蓄積）

ユーザー自身の発話を記録し、次回のAI回答生成時に
口調模倣のためのFew-shot例として活用する。
"""

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class UserUtterance:
    """ユーザー発話レコード"""
    text: str
    timestamp: float
    session_id: str
    context: str = ""  # 直前の相手の発言（任意）


class LearningStore:
    """ユーザー発話の永続化と取得"""

    def __init__(self, data_dir: Path):
        self.file_path = data_dir / "user_profile" / "utterances.jsonl"
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, utterance: UserUtterance):
        """発話を記録する"""
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(utterance), ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[WARNING] 発話記録エラー: {e}")

    def get_recent_examples(self, n: int = 5) -> list[UserUtterance]:
        """直近のN件の発話例を取得する"""
        if not self.file_path.exists():
            return []

        try:
            lines: list[str] = []
            with open(self.file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 末尾からN件取得
            recent = lines[-n:] if len(lines) >= n else lines
            utterances = []
            for line in recent:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    utterances.append(UserUtterance(**data))
            return utterances
        except Exception as e:
            print(f"[WARNING] 発話読み込みエラー: {e}")
            return []

    def format_few_shot(self, examples: Optional[list[UserUtterance]] = None) -> str:
        """Few-shot用のプロンプトテキストを生成する"""
        if examples is None:
            examples = self.get_recent_examples()

        if not examples:
            return ""

        lines = ["以下はユーザーの過去の発言例です。回答を生成する際、この口調を参考にしてください：", ""]
        for i, ex in enumerate(examples, 1):
            if ex.context:
                lines.append(f"  相手: {ex.context}")
            lines.append(f"  ユーザー: {ex.text}")
            lines.append("")

        return "\n".join(lines)
