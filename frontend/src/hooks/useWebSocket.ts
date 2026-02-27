/**
 * Alter - WebSocket接続管理フック
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ClientMessage, ServerMessage } from '../types/messages';

interface UseWebSocketOptions {
    onMessage: (msg: ServerMessage) => void;
    autoConnect?: boolean;
}

interface UseWebSocketReturn {
    send: (msg: ClientMessage) => void;
    connected: boolean;
    reconnect: () => void;
}

export function useWebSocket({ onMessage, autoConnect = true }: UseWebSocketOptions): UseWebSocketReturn {
    const wsRef = useRef<WebSocket | null>(null);
    const [connected, setConnected] = useState(false);
    const onMessageRef = useRef(onMessage);
    onMessageRef.current = onMessage;

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        // 開発時はViteプロキシ、本番時は同一オリジン
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('[WS] 接続成功');
            setConnected(true);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data) as ServerMessage;
                onMessageRef.current(data);
            } catch (e) {
                console.error('[WS] メッセージ解析エラー:', e);
            }
        };

        ws.onclose = () => {
            console.log('[WS] 切断');
            setConnected(false);

            // 自動再接続（3秒後）
            setTimeout(() => {
                if (wsRef.current === ws) {
                    connect();
                }
            }, 3000);
        };

        ws.onerror = (error) => {
            console.error('[WS] エラー:', error);
        };

        wsRef.current = ws;
    }, []);

    const send = useCallback((msg: ClientMessage) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(msg));
        } else {
            console.warn('[WS] 未接続のため送信できません');
        }
    }, []);

    useEffect(() => {
        if (autoConnect) {
            connect();
        }
        return () => {
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [autoConnect, connect]);

    return { send, connected, reconnect: connect };
}
