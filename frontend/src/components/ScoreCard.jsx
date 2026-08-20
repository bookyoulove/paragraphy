export default function ScoreCard({ result }) {
  const pct = Math.round((result.score / result.totalMax) * 100);
  return (
    <div className="score-card">
      <div className="score-ring-wrap">
        <div className="score-ring" style={{ '--score': pct }}>
          <div className="score-inner">
            <span className="score-number">{result.score}</span>
            <span className="score-divider">/ {result.totalMax}</span>
          </div>
        </div>
        <div className="score-text">
          <div className="score-title">항목별 채점 결과</div>
          <div className="score-sub">각 평가 항목의 근거와 개선 방향을 확인해 보세요.</div>
        </div>
      </div>
      <div className="criteria-list">
        {result.scores.map((item) => (
          <div className="criteria-item" key={item.label}>
            <div className="criteria-row">
              <span className="criteria-label">{item.label}</span>
              <span className="criteria-score">
                {item.value} / {item.maxScore}
              </span>
            </div>
            <div className="bar">
              <span style={{ width: `${(item.value / item.maxScore) * 100}%` }} />
            </div>
            {(item.rationale || item.improvement) && (
              <div className="criteria-feedback">
                {item.rationale && (
                  <p>
                    <strong>평가</strong>
                    {item.rationale}
                  </p>
                )}
                {item.improvement && (
                  <p>
                    <strong>개선 제안</strong>
                    {item.improvement}
                  </p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
      {result.commentary && (
        <div className="checklist-box">
          <div className="checklist-title">종합 코멘트</div>
          <p className="overall-comment">{result.commentary}</p>
        </div>
      )}
    </div>
  );
}
