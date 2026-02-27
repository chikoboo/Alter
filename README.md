# ⚡ Alter

Windows上のシステム音声（マイク＝自分、スピーカー＝相手）をリアルタイムで文字起こしし、選択テキストに対してAIが回答を生成するデスクトップオーバーレイアプリ。

## 特徴

- 🎤 **リアルタイム文字起こし** — faster-whisper (large-v3) + CUDA で高速・高精度
- 🔊 **WASAPIループバック** — マイク入力（自分）とスピーカー出力（相手）を独立キャプチャ
- 🤖 **マルチLLM対応** — Gemini / OpenAI / Claude を切り替え可能
- 📋 **セッション管理** — 会議ごとにログを分離保存・復元
- 🧠 **学習ループ** — ユーザーの発話を蓄積し、口調を模倣した回答を生成（Few-shot）

## アーキテクチャ

```
Python Backend (FastAPI + WebSocket)
  ├── Audio: PyAudioWPatch (WASAPIループバック)
  ├── STT:   faster-whisper (large-v3 / CUDA)
  ├── VAD:   Silero VAD
  ├── AI:    Gemini / OpenAI / Claude (Strategy パターン)
  └── Session: JSONL永続化

React/TypeScript Frontend (Vite)
  ├── WebSocket接続管理
  ├── チャット形式の文字起こし表示
  ├── AI回答パネル
  └── 設定・セッション管理UI

pywebview → ネイティブWindowsアプリとして表示
```

## プロジェクト構成

```
Alter/
├── backend/
│   ├── main.py                  # エントリーポイント
│   ├── config.py                # 設定管理
│   ├── requirements.txt
│   ├── audio/
│   │   ├── capture.py           # マイク + ループバックキャプチャ
│   │   └── devices.py           # デバイス列挙
│   ├── transcription/
│   │   ├── engine.py            # faster-whisper統合
│   │   └── vad.py               # Silero VAD
│   ├── ai/
│   │   ├── provider_base.py     # LLMプロバイダー抽象基底
│   │   ├── gemini_provider.py
│   │   ├── openai_provider.py
│   │   ├── claude_provider.py
│   │   ├── thinking.py          # 回答生成オーケストレーター
│   │   ├── context.py           # コンテキスト構築
│   │   └── learning.py          # 学習ループ
│   ├── session/
│   │   └── manager.py           # セッション管理
│   └── ws/
│       └── router.py            # WebSocketルーター
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx              # メインアプリ
│       ├── hooks/useWebSocket.ts
│       ├── components/
│       │   ├── TranscriptView.tsx
│       │   ├── AiPanel.tsx
│       │   ├── TitleBar.tsx
│       │   ├── SettingsDialog.tsx
│       │   └── SessionSelector.tsx
│       ├── types/messages.ts
│       └── styles/globals.css
│
└── data/                        # 実行時に自動生成
    ├── sessions/                # 会議ごとのデータ
    └── user_profile/            # ユーザー発話蓄積
```

## セットアップ

### 前提条件

- Windows 10/11
- Python 3.10+
- Node.js 18+
- CUDA対応GPU（RTX系推奨）

### 1. Backend 依存関係

```cmd
cd backend
pip install -r requirements.txt
```

### 2. Frontend ビルド

```cmd
cd frontend
npm install
npm run build
```

### 3. 環境変数

使用するLLMのAPIキーを設定（最低1つ）:

```cmd
set GEMINI_API_KEY=your-gemini-api-key
set OPENAI_API_KEY=your-openai-api-key
set ANTHROPIC_API_KEY=your-anthropic-api-key
```

### 4. 起動

**プロダクションモード**（pywebviewウィンドウ）:
```cmd
cd backend
python main.py
```

**開発モード**（ブラウザ + ホットリロード）:
```cmd
:: ターミナル1: Backend
cd backend
python main.py --dev

:: ターミナル2: Frontend
cd frontend
npm run dev
```
→ ブラウザで http://localhost:5173 にアクセス

### コマンドラインオプション

```
python main.py [OPTIONS]

  --dev          開発モード（pywebviewなし）
  --port PORT    サーバーポート（デフォルト: 8765）
  --model MODEL  Whisperモデル名（デフォルト: large-v3）
  --device DEVICE  推論デバイス: cuda / cpu（デフォルト: cuda）
```

## 使い方

1. アプリ起動後、⚙️ 設定からマイクとスピーカーデバイスを選択
2. 「⏺ 録音開始」をクリック
3. 会議中の音声がリアルタイムで文字起こしされる
   - `[You]` — 自分の発言（マイク）
   - `[Target]` — 相手の発言（スピーカー）
4. テキストを選択すると、AIが回答案を生成
5. 📋 ボタンでクリップボードにコピー

## セッション管理

- 会議ごとに自動でセッションを作成
- タイトルバーのセッション名をクリックで一覧・切替
- ログは `data/sessions/` 以下にJSONL形式で保存
