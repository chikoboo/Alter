/**
 * Alter - 文字起こしログ表示コンポーネント
 * クリックで複数バブルを選択し、AIに問い合わせ可能
 */

import { useCallback, useEffect, useRef } from 'react';
import type { TranscriptEntry } from '../types/messages';

interface Props {
    entries: TranscriptEntry[];
    selectedIndices: Set<number>;
    onToggleSelect: (index: number, shiftKey: boolean) => void;
    onClearSelection: () => void;
    onAskAi: () => void;
    onTextSelect: (text: string) => void;
}

function formatTime(timestamp: number): string {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function TranscriptView({
    entries,
    selectedIndices,
    onToggleSelect,
    onClearSelection,
    onAskAi,
    onTextSelect,
}: Props) {
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

    // バブルクリック — 選択トグル
    const handleBubbleClick = useCallback((e: React.MouseEvent, index: number) => {
        // テキスト選択中ならクリック選択しない
        const selection = window.getSelection();
        if (selection && selection.toString().trim().length > 0) return;

        onToggleSelect(index, e.shiftKey);
    }, [onToggleSelect]);

    // テキスト選択のハンドリング（従来の1件部分選択）
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

    const selectionCount = selectedIndices.size;

    return (
        <>
            <div
                className="transcript-view"
                ref={containerRef}
                onScroll={handleScroll}
                onMouseUp={handleMouseUp}
            >
                {entries.map((entry, i) => {
                    const isSelected = selectedIndices.has(i);
                    return (
                        <div
                            key={i}
                            className={`transcript-bubble transcript-bubble--${entry.speaker}${isSelected ? ' transcript-bubble--selected' : ''}`}
                            onClick={(e) => handleBubbleClick(e, i)}
                        >
                            {isSelected && (
                                <div className="transcript-bubble__check">✓</div>
                            )}
                            <div className="transcript-bubble__speaker">
                                {entry.speaker === 'you' ? 'You' : 'Target'}
                            </div>
                            <div>{entry.text}</div>
                            <div className="transcript-bubble__time">
                                {formatTime(entry.timestamp)}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* フローティング選択バー */}
            {selectionCount > 0 && (
                <div className="selection-bar">
                    <span className="selection-bar__count">
                        {selectionCount}件選択中
                    </span>
                    <div className="selection-bar__actions">
                        <button className="btn btn--primary btn--sm" onClick={onAskAi}>
                            💡 AIに聞く
                        </button>
                        <button className="btn btn--sm" onClick={onClearSelection}>
                            ✕ 解除
                        </button>
                    </div>
                </div>
            )}
        </>
    );
}
