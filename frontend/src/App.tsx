/**
 * Alter - メインアプリケーション
 * 全コンポーネントの統合・状態管理
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { TitleBar } from './components/TitleBar';
import { TranscriptView } from './components/TranscriptView';
import { AiPanel } from './components/AiPanel';
import { SettingsDialog } from './components/SettingsDialog';
import { SessionSelector } from './components/SessionSelector';
import type {
    TranscriptEntry,
    Device,
    SessionInfo,
    ServerMessage,
} from './types/messages';

// --- localStorage ヘルパー ---
const STORAGE_KEYS = {
    MIC: 'alter_selected_mic',
    SPEAKER: 'alter_selected_speaker',
    PROVIDER: 'alter_llm_provider',
} as const;

function loadSetting<T>(key: string, fallback: T): T {
    try {
        const v = localStorage.getItem(key);
        return v !== null ? JSON.parse(v) : fallback;
    } catch {
        return fallback;
    }
}

function saveSetting(key: string, value: unknown) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch { /* ignore */ }
}

export function App() {
    // --- 状態 ---
    const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
    const [recording, setRecording] = useState(false);

    // AI
    const [aiAnswer, setAiAnswer] = useState<string | null>(null);
    const [aiProvider, setAiProvider] = useState(() => loadSetting(STORAGE_KEYS.PROVIDER, 'gemini'));
    const [aiLoading, setAiLoading] = useState(false);
    const [selectedText, setSelectedText] = useState('');

    // バブル選択
    const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
    const lastSelectedRef = useRef<number | null>(null);

    // デバイス
    const [microphones, setMicrophones] = useState<Device[]>([]);
    const [speakers, setSpeakers] = useState<Device[]>([]);
    const [selectedMic, setSelectedMic] = useState<number | null>(() => loadSetting(STORAGE_KEYS.MIC, null));
    const [selectedSpeaker, setSelectedSpeaker] = useState<number | null>(() => loadSetting(STORAGE_KEYS.SPEAKER, null));

    // セッション
    const [sessionName, setSessionName] = useState('');
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [sessions, setSessions] = useState<SessionInfo[]>([]);

    // プロバイダー
    const [availableProviders, setAvailableProviders] = useState<string[]>([]);

    // UI
    const [showSettings, setShowSettings] = useState(false);
    const [showSessions, setShowSessions] = useState(false);

    // 初回接続で保存済み設定を自動適用するフラグ
    const hasRestoredRef = useRef(false);

    // --- WebSocket メッセージ処理 ---
    const handleMessage = useCallback((msg: ServerMessage) => {
        switch (msg.type) {
            case 'transcript':
                setTranscripts((prev) => [...prev, {
                    speaker: msg.speaker,
                    text: msg.text,
                    timestamp: msg.timestamp,
                }]);
                break;

            case 'ai_response':
                setAiAnswer(msg.answer);
                setAiProvider(msg.provider);
                setAiLoading(false);
                break;

            case 'ai_loading':
                setAiLoading(msg.loading);
                break;

            case 'devices':
                setMicrophones(msg.microphones);
                setSpeakers(msg.speakers);
                break;

            case 'status':
                setRecording(msg.recording);
                if (msg.llm_provider) setAiProvider(msg.llm_provider);
                if (msg.available_providers) setAvailableProviders(msg.available_providers);
                if (msg.session) {
                    setSessionName(msg.session.name || '');
                    setSessionId(msg.session.id || null);
                }
                break;

            case 'session_info':
                setSessionName(msg.name);
                setSessionId(msg.id);
                break;

            case 'session_loaded':
                setSessionName(msg.name);
                setSessionId(msg.id);
                setTranscripts(msg.transcript_log || []);
                break;

            case 'sessions_list':
                setSessions(msg.sessions);
                break;

            case 'settings_updated':
                setAiProvider(msg.llm_provider);
                setAvailableProviders(msg.available_providers);
                break;

            case 'error':
                console.error('[Backend Error]', msg.message);
                break;
        }
    }, []);

    const { send, connected } = useWebSocket({ onMessage: handleMessage });

    // --- 接続時に保存済み設定を自動復元 ---
    useEffect(() => {
        if (!connected || hasRestoredRef.current) return;
        hasRestoredRef.current = true;

        // デバイス一覧を取得
        send({ type: 'get_devices' });

        // 保存済みデバイスがあればバックエンドに送信
        const savedMic = loadSetting<number | null>(STORAGE_KEYS.MIC, null);
        const savedSpeaker = loadSetting<number | null>(STORAGE_KEYS.SPEAKER, null);
        if (savedMic !== null && savedSpeaker !== null) {
            send({ type: 'select_devices', mic_id: savedMic, speaker_id: savedSpeaker });
        }

        // 保存済みプロバイダーがあれば送信
        const savedProvider = loadSetting(STORAGE_KEYS.PROVIDER, '');
        if (savedProvider) {
            send({ type: 'settings', llm_provider: savedProvider as 'gemini' | 'openai' | 'claude' });
        }
    }, [connected, send]);

    // --- イベントハンドラ ---

    const handleToggleRecording = () => {
        if (recording) {
            send({ type: 'recording', action: 'stop' });
        } else {
            send({ type: 'recording', action: 'start' });
        }
    };

    const handleTextSelect = (text: string) => {
        setSelectedText(text);
        setAiAnswer(null);
        setAiLoading(true);
        send({ type: 'ai_request', selected_text: text });
    };

    // バブル選択トグル（Shift+クリック = 範囲選択）
    const handleToggleSelect = useCallback((index: number, shiftKey: boolean) => {
        setSelectedIndices((prev) => {
            const next = new Set(prev);
            if (shiftKey && lastSelectedRef.current !== null) {
                const from = Math.min(lastSelectedRef.current, index);
                const to = Math.max(lastSelectedRef.current, index);
                for (let i = from; i <= to; i++) {
                    next.add(i);
                }
            } else {
                if (next.has(index)) {
                    next.delete(index);
                } else {
                    next.add(index);
                }
            }
            return next;
        });
        lastSelectedRef.current = index;
    }, []);

    const handleClearSelection = useCallback(() => {
        setSelectedIndices(new Set());
        lastSelectedRef.current = null;
    }, []);

    const handleAskAiFromSelection = useCallback(() => {
        if (selectedIndices.size === 0) return;
        // 選択バブルのテキストを時系列順に結合
        const sortedIndices = Array.from(selectedIndices).sort((a, b) => a - b);
        const combined = sortedIndices
            .map((i) => {
                const e = transcripts[i];
                if (!e) return '';
                const label = e.speaker === 'you' ? 'You' : 'Target';
                return `[${label}] ${e.text}`;
            })
            .filter(Boolean)
            .join('\n');

        setSelectedText(combined);
        setAiAnswer(null);
        setAiLoading(true);
        send({ type: 'ai_request', selected_text: combined });
        handleClearSelection();
    }, [selectedIndices, transcripts, send, handleClearSelection]);

    const handleSelectDevices = (micId: number, speakerId: number) => {
        setSelectedMic(micId);
        setSelectedSpeaker(speakerId);
        saveSetting(STORAGE_KEYS.MIC, micId);
        saveSetting(STORAGE_KEYS.SPEAKER, speakerId);
        send({ type: 'select_devices', mic_id: micId, speaker_id: speakerId });
    };

    const handleChangeProvider = (provider: string) => {
        saveSetting(STORAGE_KEYS.PROVIDER, provider);
        send({ type: 'settings', llm_provider: provider as 'gemini' | 'openai' | 'claude' });
    };

    const handleNewSession = () => {
        send({ type: 'session_action', action: 'new' });
        setTranscripts([]);
        setAiAnswer(null);
        setShowSessions(false);
    };

    const handleSwitchSession = (sid: string) => {
        send({ type: 'session_action', action: 'switch', session_id: sid });
    };

    const handleOpenSettings = () => {
        send({ type: 'get_devices' });
        setShowSettings(true);
    };

    const handleOpenSessions = () => {
        send({ type: 'get_sessions' });
        setShowSessions(true);
    };

    const handleCopyAnswer = () => {
        if (aiAnswer) {
            navigator.clipboard.writeText(aiAnswer);
        }
    };

    // --- レンダリング ---

    return (
        <div className="app">
            <TitleBar
                sessionName={sessionName}
                connected={connected}
                onSettingsClick={handleOpenSettings}
                onSessionsClick={handleOpenSessions}
            />

            <div className="control-bar">
                <div className="control-bar__group">
                    <button
                        className={`btn ${recording ? 'btn--danger' : 'btn--primary'}`}
                        onClick={handleToggleRecording}
                    >
                        {recording ? '⏹ 停止' : '⏺ 録音開始'}
                    </button>
                </div>
                <div className="control-bar__group">
                    <span className="text-sm text-muted">
                        {recording ? '🔴 録音中...' : '⏸ 待機中'}
                    </span>
                </div>
            </div>

            <TranscriptView
                entries={transcripts}
                selectedIndices={selectedIndices}
                onToggleSelect={handleToggleSelect}
                onClearSelection={handleClearSelection}
                onAskAi={handleAskAiFromSelection}
                onTextSelect={handleTextSelect}
            />

            <AiPanel
                answer={aiAnswer}
                provider={aiProvider}
                selectedText={selectedText}
                loading={aiLoading}
                onClose={() => { setAiAnswer(null); setAiLoading(false); }}
                onCopy={handleCopyAnswer}
            />

            {showSettings && (
                <SettingsDialog
                    microphones={microphones}
                    speakers={speakers}
                    selectedMic={selectedMic}
                    selectedSpeaker={selectedSpeaker}
                    currentProvider={aiProvider}
                    availableProviders={availableProviders}
                    onSelectDevices={handleSelectDevices}
                    onChangeProvider={handleChangeProvider}
                    onClose={() => setShowSettings(false)}
                />
            )}

            {showSessions && (
                <SessionSelector
                    sessions={sessions}
                    currentSessionId={sessionId}
                    onSwitch={handleSwitchSession}
                    onNew={handleNewSession}
                    onClose={() => setShowSessions(false)}
                />
            )}
        </div>
    );
}
