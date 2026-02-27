/**
 * Alter - カスタムタイトルバー
 */

interface Props {
    sessionName: string;
    connected: boolean;
    onSettingsClick: () => void;
    onSessionsClick: () => void;
}

export function TitleBar({ sessionName, connected, onSettingsClick, onSessionsClick }: Props) {
    return (
        <div className="title-bar">
            <div className="title-bar__left">
                <span className="title-bar__logo">⚡ Alter</span>
                {sessionName && (
                    <button
                        className="title-bar__session"
                        onClick={onSessionsClick}
                        title="セッション切替"
                    >
                        {sessionName}
                    </button>
                )}
            </div>
            <div className="title-bar__right">
                <span
                    className={`title-bar__status ${connected ? 'connected' : 'disconnected'}`}
                    title={connected ? '接続中' : '未接続'}
                />
                <button className="btn btn--icon btn--sm" onClick={onSettingsClick} title="設定">
                    ⚙️
                </button>
            </div>
        </div>
    );
}
