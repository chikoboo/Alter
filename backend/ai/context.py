"""Alter - コンテキスト構築

選択されたテキストと直近のログ、学習データを統合して
LLMに送るプロンプトを構築する。
"""

from dataclasses import dataclass

from backend.ai.learning import LearningStore


@dataclass
class ContextPayload:
    """LLMに送信するコンテキスト"""
    system_prompt: str
    user_prompt: str


class ContextBuilder:
    """コンテキスト構築"""

    SYSTEM_PROMPT_TEMPLATE = """あなたはWeb会議中のユーザーを支援するアシスタントです。
ユーザーが会議中に選択したテキスト（相手の発言や自分の発言）に基づいて、
適切な回答案や提案を生成してください。

ルール:
- 回答は簡潔かつ実用的にしてください
- 会議の文脈を踏まえた自然な回答を心がけてください
- 日本語で回答してください
- 回答案として使えるよう、そのまま発言できる形式にしてください

{few_shot_section}"""

    USER_PROMPT_TEMPLATE = """## 会議の直近の会話ログ:
{conversation_log}

## ユーザーが選択したテキスト（これについて回答を生成してください）:
{selected_text}"""

    def __init__(self, learning_store: LearningStore, max_context_lines: int = 30):
        self.learning_store = learning_store
        self.max_context_lines = max_context_lines

    def build(
        self,
        selected_text: str,
        transcript_log: list[dict],
        context_lines: int | None = None,
    ) -> ContextPayload:
        """コンテキストを構築する

        Args:
            selected_text: ユーザーが選択したテキスト
            transcript_log: 文字起こしログ [{"speaker": "you"|"target", "text": "..."}]
            context_lines: 使用するログ行数（Noneの場合はmax_context_lines）

        Returns:
            LLMに送信するプロンプトペア
        """
        n = context_lines if context_lines is not None else self.max_context_lines

        # 直近N行のログを構築
        recent_log = transcript_log[-n:] if len(transcript_log) > n else transcript_log
        conversation_lines = []
        for entry in recent_log:
            speaker_label = "[You]" if entry.get("speaker") == "you" else "[Target]"
            conversation_lines.append(f"{speaker_label} {entry.get('text', '')}")
        conversation_log = "\n".join(conversation_lines) if conversation_lines else "(会話ログなし)"

        # Few-shot セクション
        few_shot_section = self.learning_store.format_few_shot()

        # プロンプト構築
        system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(
            few_shot_section=few_shot_section,
        )
        user_prompt = self.USER_PROMPT_TEMPLATE.format(
            conversation_log=conversation_log,
            selected_text=selected_text,
        )

        return ContextPayload(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
