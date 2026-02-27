/**
 * Alter - メインアプリケーション
 * 全コンポーネントの統合・状態管理
 */

import { useCallback, useState } from 'react';
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

export function App() {
    // --- 状態 ---
    const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
    const [recording, setRecording] = useState(false);

    // AI
    const [aiAnswer, setAiAnswer] = useState<string | null>(null);
    const [aiProvider, setAiProvider] = useState('gemini');
    const [aiLoading, setAiLoading] = useState(false);
    const [selectedText, setSelectedText] = useState('');

    // デバイス
    const [microphones, setMicrophones] = useState<Device[]>([]);
    const [speakers, setSpeakers] = useState<Device[]>([]);
    const [selectedMic, setSelectedMic] = useState<number | null>(null);
    const [selectedSpeaker, setSelectedSpeaker] = useState<number | null>(null);

    // セッション
    const [sessionName, setSessionName] = useState('');
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [sessions, setSessions] = useState<SessionInfo[]>([]);

    // プロバイダー
    const [availableProviders, setAvailableProviders] = useState<string[]>([]);

    // UI
    const [showSettings, setShowSettings] = useState(false);
    const [showSessions, setShowSessions] = useState(false);

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

    const handleSelectDevices = (micId: number, speakerId: number) => {
        setSelectedMic(micId);
        setSelectedSpeaker(speakerId);
        send({ type: 'select_devices', mic_id: micId, speaker_id: speakerId });
    };

    const handleChangeProvider = (provider: string) => {
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
