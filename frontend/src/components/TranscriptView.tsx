/**
 * Alter - 文字起こしログ表示コンポーネント
 */

import { useEffect, useRef } from 'react';
import type { TranscriptEntry } from '../types/messages';

interface Props {
    entries: TranscriptEntry[];
    onTextSelect: (text: string) => void;
}

function formatTime(timestamp: number): string {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function TranscriptView({ entries, onTextSelect }: Props) {
    const containerRef = useRef<HTMLDivElement>(null);
    const isAutoScrollRef = useRef(true);

    // 自動スクロール
    useEffect(() => {
        if (isAutoScrollRef.current && containerRef.current) {
            containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
    }, [entries]);

    // スクロール位置の追跡
    const handleScroll = () => {
        if (!containerRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
        isAutoScrollRef.current = scrollHeight - scrollTop - clientHeight < 50;
    };

    // テキスト選択のハンドリング
    const handleMouseUp = () => {
        const selection = window.getSelection();
        const selectedText = selection?.toString().trim();
        if (selectedText && selectedText.length > 0) {
            onTextSelect(selectedText);
        }
    };

    if (entries.length === 0) {
        return (
            <div className="transcript-view">
                <div className="transcript-empty">
                    <div className="transcript-empty__icon">🎙️</div>
                    <div className="transcript-empty__text">
                        録音を開始すると<br />文字起こしがここに表示されます
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div
            className="transcript-view"
            ref={containerRef}
            onScroll={handleScroll}
            onMouseUp={handleMouseUp}
        >
            {entries.map((entry, i) => (
                <div
                    key={i}
                    className={`transcript-bubble transcript-bubble--${entry.speaker}`}
                >
                    <div className="transcript-bubble__speaker">
                        {entry.speaker === 'you' ? 'You' : 'Target'}
                    </div>
                    <div>{entry.text}</div>
                    <div className="transcript-bubble__time">
                        {formatTime(entry.timestamp)}
                    </div>
                </div>
            ))}
        </div>
    );
}
