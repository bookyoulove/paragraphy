export default function RubricItems({ items = [], readOnly = false, onChange }) {
  const editable = !readOnly && typeof onChange === 'function';

  const updateItem = (index, field, value) => {
    onChange(
      items.map((item, itemIndex) => (itemIndex === index ? { ...item, [field]: value } : item)),
    );
  };

  const addItem = () => {
    onChange([...items, { criteria: '', description: '' }]);
  };

  const removeItem = (index) => {
    onChange(items.filter((_, itemIndex) => itemIndex !== index));
  };

  return (
    <>
      {items.length ? (
        <div className="rubric-list">
          {items.map((item, index) => (
            <article
              className={`rubric-item ${editable ? 'rubric-item-editable' : 'rubric-item-readonly'}`}
              key={item.id ?? index}
            >
              {editable ? (
                <>
                  <div className="rubric-item-edit-header">
                    <span className="rubric-item-index">{index + 1}. 채점 기준</span>
                    <button
                      type="button"
                      className="ghost-btn rubric-remove-button"
                      onClick={() => removeItem(index)}
                    >
                      삭제
                    </button>
                  </div>
                  <label className="rubric-item-field">
                    <span className="rubric-item-label">기준 제목</span>
                    <input
                      className="rubric-item-input"
                      value={item.criteria ?? ''}
                      onChange={(event) => updateItem(index, 'criteria', event.target.value)}
                    />
                  </label>
                  <label className="rubric-item-field">
                    <span className="rubric-item-label">내용</span>
                    <textarea
                      className="rubric-item-textarea"
                      value={item.description ?? ''}
                      onChange={(event) => updateItem(index, 'description', event.target.value)}
                    />
                  </label>
                </>
              ) : (
                <>
                  <div className="rubric-item-title">
                    <span className="rubric-item-number">{index + 1}.</span>
                    {item.criteria || '채점 기준'}
                  </div>
                  <div className="rubric-item-description">
                    {item.description || '설명이 없습니다.'}
                  </div>
                </>
              )}
            </article>
          ))}
        </div>
      ) : (
        <div className="rubric-empty">등록된 채점 기준이 없습니다.</div>
      )}
      {editable && (
        <div className="rubric-editor-actions">
          <button type="button" className="ghost-btn" onClick={addItem}>
            채점 기준 추가
          </button>
        </div>
      )}
    </>
  );
}
