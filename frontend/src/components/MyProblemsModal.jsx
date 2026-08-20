import { useState } from 'react';

export default function MyProblemsModal({ problems, onSelect, onDelete, onClose }) {
  const [deletingId, setDeletingId] = useState(null);

  const removeProblem = async (event, problem) => {
    event.stopPropagation();
    if (!window.confirm('이 문제를 삭제할까요? 이 문제로 작성한 답안과 채점 결과도 함께 삭제됩니다.')) return;
    setDeletingId(problem.id);
    try {
      await onDelete(problem.id);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="rubric-modal">
      <div className="rubric-modal-backdrop" onClick={onClose} />
      <div className="rubric-modal-card">
        <div className="rubric-modal-header">
          <div className="label-title">직접 입력한 문제 목록</div>
          <button className="ghost-btn" onClick={onClose}>
            닫기 ✕
          </button>
        </div>
        <div className="rubric-modal-body">
          {problems.length ? (
            <div className="problem-list">
              {problems.map((problem) => (
                <div className="problem-card round-card" key={problem.id}>
                  <button className="round-card-main" onClick={() => onSelect(problem)}>
                    <span className="card-title">{problem.title}</span>
                    <span className="card-meta">직접 입력</span>
                  </button>
                  {onDelete && (
                    <button
                      className="ghost-btn round-delete-btn"
                      disabled={deletingId === problem.id}
                      onClick={(event) => removeProblem(event, problem)}
                    >
                      {deletingId === problem.id ? '삭제 중...' : '삭제'}
                    </button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="panel-empty">아직 직접 입력한 문제가 없습니다.</div>
          )}
        </div>
      </div>
    </div>
  );
}
