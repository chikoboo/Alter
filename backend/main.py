"""Alter - メインエントリーポイント

FastAPIサーバーを起動し、pywebviewでネイティブウィンドウを表示する。
開発時は通常のブラウザでも接続可能。
"""

import sys
import threading
import argparse
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from config import AppConfig
from ws.router import router, init_backend


def create_app(config: AppConfig) -> FastAPI:
    """FastAPIアプリケーションを作成"""
    app = FastAPI(title="Alter", version="0.1.0")

    # CORS設定（開発時のフロントエンド開発サーバーからの接続用）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # WebSocketルーター
    app.include_router(router)

    # ビルド済みフロントエンドの静的ファイル配信
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    # バックエンド初期化
    init_backend(config)

    return app


def start_server(config: AppConfig):
    """FastAPIサーバーを起動する"""
    app = create_app(config)
    uvicorn.run(app, host=config.host, port=config.port, log_level="info")


def start_with_webview(config: AppConfig):
    """pywebviewでネイティブウィンドウを起動する"""
    try:
        import webview
    except ImportError:
        print("[ERROR] pywebview がインストールされていません")
        print("[INFO] ブラウザモードで起動します")
        start_server(config)
        return

    # サーバーをバックグラウンドスレッドで起動
    server_thread = threading.Thread(
        target=start_server,
        args=(config,),
        daemon=True,
    )
    server_thread.start()

    # pywebviewウィンドウを作成
    url = f"http://{config.host}:{config.port}"
    window = webview.create_window(
        "Alter",
        url=url,
        width=480,
        height=700,
        resizable=True,
        on_top=True,
        frameless=False,
        easy_drag=True,
    )
    webview.start()


def main():
    parser = argparse.ArgumentParser(description="Alter - リアルタイム文字起こし + AI回答")
    parser.add_argument("--dev", action="store_true", help="開発モード（pywebviewなし、ブラウザで接続）")
    parser.add_argument("--port", type=int, default=8765, help="サーバーポート")
    parser.add_argument("--model", default="large-v3", help="Whisperモデル名")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"], help="推論デバイス")
    args = parser.parse_args()

    config = AppConfig(
        port=args.port,
        whisper_model=args.model,
        whisper_device=args.device,
    )

    print("=" * 50)
    print("  Alter - リアルタイム文字起こし + AI回答")
    print("=" * 50)
    print(f"  Whisperモデル: {config.whisper_model}")
    print(f"  推論デバイス:  {config.whisper_device}")
    print(f"  LLMプロバイダー: {config.llm_provider}")
    print(f"  サーバー:      http://{config.host}:{config.port}")
    print("=" * 50)

    if args.dev:
        print("[DEV] 開発モード - ブラウザで http://localhost:5173 に接続してください")
        start_server(config)
    else:
        start_with_webview(config)


if __name__ == "__main__":
    main()
