export default function ProblemPicker({ problems, selectedId, onSelect, onRefresh }) {
  const personalizedProblems = problems.filter((problem) => problem.raw.source_report_id);
  const regularProblems = problems.filter((problem) => !problem.raw.source_report_id);
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
      {personalizedProblems.length > 0 && (
        <section className="personalized-problem-section">
          <div className="personalized-problem-heading">AI 맞춤 문제</div>
          {personalizedProblems.map((problem) => (
            <button key={problem.id} className="problem-card personalized-problem-card" onClick={() => onSelect(problem)}>
              <span className="card-title">{problem.title}</span>
              <span className="card-meta">최근 분석 리포트를 바탕으로 취약한 부분을 보완하도록 만든 문제입니다.</span>
            </button>
          ))}
        </section>
      )}
      <div className="problem-list">
        {regularProblems.map((problem) => (
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
