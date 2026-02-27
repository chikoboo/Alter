/**
 * Alter - セッションセレクター
 */

import type { SessionInfo } from '../types/messages';

interface Props {
    sessions: SessionInfo[];
    currentSessionId: string | null;
    onSwitch: (sessionId: string) => void;
    onNew: () => void;
    onClose: () => void;
}

export function SessionSelector({ sessions, currentSessionId, onSwitch, onNew, onClose }: Props) {
    return (
        <div className="dialog-overlay" onClick={onClose}>
            <div className="dialog" onClick={(e) => e.stopPropagation()}>
                <div className="dialog__header">
                    <span className="dialog__title">📋 セッション一覧</span>
                    <button className="btn btn--icon btn--sm" onClick={onClose}>✕</button>
                </div>

                <div className="dialog__body">
                    <button className="btn btn--primary" onClick={onNew} style={{ width: '100%' }}>
                        ＋ 新規セッション
                    </button>

                    <div className="session-list">
                        {sessions.map((s) => (
                            <div
                                key={s.id}
                                className={`session-item ${s.id === currentSessionId ? 'active' : ''}`}
                                onClick={() => { onSwitch(s.id); onClose(); }}
                            >
                                <span className="session-item__name">{s.name}</span>
                                <span className="session-item__date">
                                    {new Date(s.created_at).toLocaleDateString('ja-JP', {
                                        month: 'short',
                                        day: 'numeric',
                                        hour: '2-digit',
                                        minute: '2-digit',
                                    })}
                                </span>
                            </div>
                        ))}
                        {sessions.length === 0 && (
                            <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>
                                セッションがありません
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
