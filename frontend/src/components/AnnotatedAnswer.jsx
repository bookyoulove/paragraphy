import { useMemo } from 'react';

function buildSegments(text, corrections) {
  const segments = [];
  let cursor = 0;

  corrections.forEach((correction, correctionIndex) => {
    const before = correction.before?.trim();
    if (!before) return;
    const index = text.indexOf(before, cursor);
    if (index === -1) return;
    if (index > cursor) segments.push({ type: 'text', value: text.slice(cursor, index) });
    segments.push({ type: 'correction', value: before, correction, correctionIndex });
    cursor = index + before.length;
  });
  if (cursor < text.length) segments.push({ type: 'text', value: text.slice(cursor) });
  return segments;
}

export default function AnnotatedAnswer({ text, corrections = [], selectedIndex, onSelect }) {
  const segments = useMemo(() => buildSegments(text, corrections), [text, corrections]);
  const selected = selectedIndex === null ? null : corrections[selectedIndex];

  return (
    <div className="annotated-answer-wrap">
      {selected && (
        <div className="answer-correction-callout" role="status">
          <div>
            <span className="answer-correction-label">첨삭 제안</span>
            <del>{selected.before}</del>
            <span className="answer-correction-arrow">→</span>
            <strong>{selected.after}</strong>
            {selected.note && <p>{selected.note}</p>}
          </div>
          <button type="button" onClick={() => onSelect(null)} aria-label="첨삭 제안 닫기">×</button>
        </div>
      )}
      <div className="annotated-answer" aria-label="첨삭이 표시된 답안">
        {segments.map((segment, index) =>
          segment.type === 'text' ? (
            <span key={`text-${index}`}>{segment.value}</span>
          ) : (
            <button
              type="button"
              key={`correction-${index}`}
              className={`answer-correction-mark ${selectedIndex === segment.correctionIndex ? 'active' : ''}`}
              onClick={() => onSelect(segment.correctionIndex)}
              title={`첨삭 제안: ${segment.correction.after}`}
              aria-pressed={selectedIndex === segment.correctionIndex}
            >
              {segment.value}
            </button>
          ),
        )}
      </div>
      {corrections.length > 0 && (
        <p className="annotated-answer-hint">빨간 밑줄 문장을 누르면 첨삭 제안을 볼 수 있어요.</p>
      )}
    </div>
  );
}
