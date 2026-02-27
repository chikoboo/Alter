/**
 * Alter - 設定ダイアログ
 * デバイス選択 + LLMプロバイダー選択
 */

import { useState } from 'react';
import type { Device } from '../types/messages';

interface Props {
    microphones: Device[];
    speakers: Device[];
    selectedMic: number | null;
    selectedSpeaker: number | null;
    currentProvider: string;
    availableProviders: string[];
    onSelectDevices: (micId: number, speakerId: number) => void;
    onChangeProvider: (provider: string) => void;
    onClose: () => void;
}

const providerLabels: Record<string, string> = {
    gemini: '🟦 Gemini (gemini-2.0-flash)',
    openai: '🟩 OpenAI (gpt-4o-mini)',
    claude: '🟧 Claude (claude-3-5-haiku)',
};

export function SettingsDialog({
    microphones,
    speakers,
    selectedMic,
    selectedSpeaker,
    currentProvider,
    availableProviders,
    onSelectDevices,
    onChangeProvider,
    onClose,
}: Props) {
    const [micId, setMicId] = useState<number>(selectedMic ?? microphones[0]?.index ?? 0);
    const [speakerId, setSpeakerId] = useState<number>(selectedSpeaker ?? speakers[0]?.index ?? 0);

    const handleSave = () => {
        onSelectDevices(micId, speakerId);
        onClose();
    };

    return (
        <div className="dialog-overlay" onClick={onClose}>
            <div className="dialog" onClick={(e) => e.stopPropagation()}>
                <div className="dialog__header">
                    <span className="dialog__title">⚙️ 設定</span>
                    <button className="btn btn--icon btn--sm" onClick={onClose}>✕</button>
                </div>

                <div className="dialog__body">
                    {/* マイク選択 */}
                    <div className="form-group">
                        <label className="form-group__label">🎤 マイク（自分の声）</label>
                        <select
                            className="form-select"
                            value={micId}
                            onChange={(e) => setMicId(Number(e.target.value))}
                        >
                            {microphones.map((d) => (
                                <option key={d.index} value={d.index}>{d.name}</option>
                            ))}
                            {microphones.length === 0 && (
                                <option disabled>デバイスが見つかりません</option>
                            )}
                        </select>
                    </div>

                    {/* スピーカー選択 */}
                    <div className="form-group">
                        <label className="form-group__label">🔊 スピーカー（相手の声）</label>
                        <select
                            className="form-select"
                            value={speakerId}
                            onChange={(e) => setSpeakerId(Number(e.target.value))}
                        >
                            {speakers.map((d) => (
                                <option key={d.index} value={d.index}>{d.name}</option>
                            ))}
                            {speakers.length === 0 && (
                                <option disabled>ループバックデバイスが見つかりません</option>
                            )}
                        </select>
                    </div>

                    {/* LLMプロバイダー選択 */}
                    <div className="form-group">
                        <label className="form-group__label">🤖 AIプロバイダー</label>
                        <select
                            className="form-select"
                            value={currentProvider}
                            onChange={(e) => onChangeProvider(e.target.value)}
                        >
                            {['gemini', 'openai', 'claude'].map((p) => (
                                <option
                                    key={p}
                                    value={p}
                                    disabled={availableProviders.length > 0 && !availableProviders.includes(p)}
                                >
                                    {providerLabels[p] || p}
                                    {!availableProviders.includes(p) ? ' (APIキー未設定)' : ''}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                <div className="dialog__footer">
                    <button className="btn" onClick={onClose}>キャンセル</button>
                    <button className="btn btn--primary" onClick={handleSave}>保存</button>
                </div>
            </div>
        </div>
    );
}
