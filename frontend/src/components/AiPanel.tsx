/**
 * Alter - AI回答表示パネル
 */

interface Props {
    answer: string | null;
    provider: string;
    selectedText: string;
    loading: boolean;
    onClose: () => void;
    onCopy: () => void;
}

export function AiPanel({ answer, provider, selectedText, loading, onClose, onCopy }: Props) {
    if (!loading && !answer) return null;

    return (
        <div className="ai-panel">
            <div className="ai-panel__header">
                <div className="ai-panel__title">
                    💡 AI回答
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="ai-panel__provider">{provider}</span>
                    <button className="btn btn--icon btn--sm" onClick={onClose} title="閉じる">
                        ✕
                    </button>
                </div>
            </div>
            <div className="ai-panel__body">
                {selectedText && (
                    <div className="ai-panel__selected-text">
                        {selectedText}
                    </div>
                )}
                {loading ? (
                    <div className="ai-panel__loading">
                        <div className="loading-dots">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                        回答を生成中...
                    </div>
                ) : (
                    <>
                        <div className="ai-panel__answer">{answer}</div>
                        <div className="ai-panel__actions">
                            <button className="btn btn--primary btn--sm" onClick={onCopy}>
                                📋 コピー
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
