import { useState } from 'react'
import RubricEditor from './RubricEditor.jsx'

// 채점 기준(루브릭) 목록은 기본 접힌 상태 — 제목을 클릭하면 펼쳐진다.
export default function RubricSection({ items, editable, onChange, onSuggest, suggesting }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rubric-section">
      <button type="button" className="rubric-section-toggle" onClick={() => setOpen((v) => !v)}>
        <span className={`chevron ${open ? 'chevron-open' : ''}`}>▸</span>
        채점 기준 보기{items.length > 0 ? ` (${items.length}개)` : ''}
      </button>
      {open && (
        <RubricEditor items={items} editable={editable} onChange={onChange} onSuggest={onSuggest} suggesting={suggesting} />
      )}
    </div>
  )
}