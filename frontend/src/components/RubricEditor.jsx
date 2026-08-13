import { cleanRubricText } from '../utils'

export default function RubricEditor({ items, editable, onChange, onSuggest, suggesting }) {
  const update = (idx, field, value) => {
    const next = items.map((it, i) => (i === idx ? { ...it, [field]: value } : it))
    onChange(next)
  }
  const removeItem = (idx) => onChange(items.filter((_, i) => i !== idx))
  const addItem = () => onChange([...items, { criteria: '', description: '', max_score: 5 }])

  return (
    <div className="rubric-editor">
      <div className="rubric-editor-header">
        <span>채점 기준 (전 항목 5점 만점)</span>
        {onSuggest && (
          <button type="button" onClick={onSuggest} disabled={suggesting}>
            {suggesting ? 'AI 제안 생성 중…' : 'AI 제안 받기'}
          </button>
        )}
      </div>
      {items.length === 0 && <p className="muted">채점 기준이 없습니다. {editable ? '직접 추가하거나 AI 제안을 받아보세요.' : ''}</p>}
      {items.map((item, idx) => (
        <div className="rubric-item" key={idx}>
          {editable ? (
            <>
              <input
                className="rubric-item-name"
                value={item.criteria}
                placeholder="항목명"
                onChange={(e) => update(idx, 'criteria', e.target.value)}
              />
              <textarea
                className="rubric-item-desc"
                value={item.description || ''}
                placeholder="판단 기준 설명"
                onChange={(e) => update(idx, 'description', e.target.value)}
              />
              <button type="button" className="rubric-item-remove" onClick={() => removeItem(idx)}>
                삭제
              </button>
            </>
          ) : (
            <>
              <strong>{item.criteria}</strong>
              <p className="muted">{cleanRubricText(item.description)}</p>
            </>
          )}
        </div>
      ))}
      {editable && (
        <button type="button" className="rubric-add" onClick={addItem}>
          + 항목 추가
        </button>
      )}
    </div>
  )
}
