export default function ProblemPicker({ problems, selectedId, onSelect, onRefresh }) {
  return (
    <div className="picker-view">
      <div className="picker-view-header">
        <div>
          <div className="label-title">문제 선택</div>
          <div className="label-sub">
            등록된 문제 중 하나를 선택하면 바로 답안 작성으로 이동합니다.
          </div>
        </div>
        <button className="ghost-btn" onClick={onRefresh}>
          문제 새로고침
        </button>
      </div>
      <div className="problem-list">
        {problems.map((problem) => (
          <button
            key={problem.id}
            className={`problem-card ${selectedId === problem.id ? 'selected' : ''}`}
            onClick={() => onSelect(problem)}
          >
            <span className="card-title">{problem.title}</span>
            <span className="card-meta">
              {[problem.meta.school, problem.meta.exam_type, problem.meta.year]
                .filter(Boolean)
                .join(' · ')}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
