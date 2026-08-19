import { useEffect, useState } from 'react';
import RubricItems from './RubricItems';

function copyRubricItems(rubric) {
  return Array.isArray(rubric) ? rubric.map((item) => ({ ...item })) : [];
}

export default function RubricModal({ rubric, onClose, readOnly }) {
  const [items, setItems] = useState(() => copyRubricItems(rubric));

  useEffect(() => {
    setItems(copyRubricItems(rubric));
  }, [rubric]);

  return (
    <div className="rubric-modal">
      <div className="rubric-modal-backdrop" onClick={onClose} />
      <div className="rubric-modal-card">
        <div className="rubric-modal-header">
          <div className="label-title">채점 기준</div>
          <button className="ghost-btn" onClick={onClose}>
            닫기 ✕
          </button>
        </div>
        <div className="rubric-modal-body">
          <RubricItems items={items} readOnly={readOnly} onChange={setItems} />
        </div>
      </div>
    </div>
  );
}
