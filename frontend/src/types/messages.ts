/**
 * Alter - WebSocketメッセージ型定義
 */

// --- Backend → Frontend ---

export interface TranscriptMessage {
    type: 'transcript';
    speaker: 'you' | 'target';
    text: string;
    timestamp: number;
}

export interface AiResponseMessage {
    type: 'ai_response';
    answer: string;
    provider: string;
}

export interface AiLoadingMessage {
    type: 'ai_loading';
    loading: boolean;
}

export interface DevicesMessage {
    type: 'devices';
    microphones: Device[];
    speakers: Device[];
}

export interface StatusMessage {
    type: 'status';
    recording: boolean;
    model_loaded?: boolean;
    llm_provider?: string;
    available_providers?: string[];
    session?: SessionInfo;
}

export interface SessionInfoMessage {
    type: 'session_info';
    id: string;
    name: string;
    created_at: string;
}

export interface SessionLoadedMessage {
    type: 'session_loaded';
    id: string;
    name: string;
    created_at: string;
    transcript_log: TranscriptEntry[];
}

export interface SessionsListMessage {
    type: 'sessions_list';
    sessions: SessionInfo[];
}

export interface SettingsUpdatedMessage {
    type: 'settings_updated';
    llm_provider: string;
    available_providers: string[];
}

export interface ErrorMessage {
    type: 'error';
    message: string;
}

export type ServerMessage =
    | TranscriptMessage
    | AiResponseMessage
    | AiLoadingMessage
    | DevicesMessage
    | StatusMessage
    | SessionInfoMessage
    | SessionLoadedMessage
    | SessionsListMessage
    | SettingsUpdatedMessage
    | ErrorMessage;

// --- Frontend → Backend ---

export interface AiRequestMessage {
    type: 'ai_request';
    selected_text: string;
    context_lines?: number;
}

export interface SelectDevicesMessage {
    type: 'select_devices';
    mic_id: number;
    speaker_id: number;
}

export interface RecordingMessage {
    type: 'recording';
    action: 'start' | 'stop';
}

export interface SessionActionMessage {
    type: 'session_action';
    action: 'new' | 'switch' | 'rename';
    session_id?: string;
    name?: string;
}

export interface SettingsMessage {
    type: 'settings';
    llm_provider: 'gemini' | 'openai' | 'claude';
}

export type ClientMessage =
    | AiRequestMessage
    | SelectDevicesMessage
    | RecordingMessage
    | SessionActionMessage
    | SettingsMessage
    | { type: 'get_devices' }
    | { type: 'get_status' }
    | { type: 'get_sessions' };

// --- 共通型 ---

export interface Device {
    index: number;
    name: string;
}

export interface SessionInfo {
    id: string;
    name: string;
    created_at: string;
}

export interface TranscriptEntry {
    speaker: 'you' | 'target';
    text: string;
    timestamp: number;
}
