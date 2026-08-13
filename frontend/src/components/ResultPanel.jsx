function ScoreBar({ score, maxScore }) {
  const pct = (score / maxScore) * 100
  const color = score >= 4 ? '#2f9e44' : score >= 3 ? '#f08c00' : '#e03131'
  return (
    <div className="score-bar-track">
      <div className="score-bar-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  )
}

export function GradingTab({ result }) {
  if (!result) return <p className="muted">아직 채점 결과가 없습니다. 왼쪽에서 답안을 작성하고 "채점 요청"을 눌러주세요.</p>

  const maxTotal = result.criteria_scores.length * 5

  return (
    <div className="grading-tab">
      <div className="score-badge-row">
        <div className="score-badge">
          <span className="score-badge-value">{result.total_score}</span>
          <span className="score-badge-max">/ {maxTotal}</span>
        </div>
        <div className="score-badge-meta">
          <strong>{result.round}차 제출 채점 결과</strong>
          <p className="muted">{result.overall_comment}</p>
        </div>
      </div>

      {result.policy_warning && <div className="banner banner-warn">⚠ 검증 에이전트 경고: {result.policy_warning}</div>}

      {result.previous_comparison && (
        <div className="comparison">
          <strong>이전 차수 대비 변화</strong>
          <p className="muted">
            {result.previous_comparison.previous_total_score} → {result.previous_comparison.current_total_score}점 (
            {result.previous_comparison.total_delta >= 0 ? '+' : ''}
            {result.previous_comparison.total_delta})
          </p>
        </div>
      )}

      <div className="criterion-list">
        {result.criteria_scores.map((c) => (
          <div className="criterion-row" key={c.criterion}>
            <div className="criterion-head">
              <span>{c.criterion}</span>
              <span>
                {c.score} / {c.max_score}
              </span>
            </div>
            <ScoreBar score={c.score} maxScore={c.max_score} />
          </div>
        ))}
      </div>

      <div className="revision-directions">
        <strong>수정 방향성</strong>
        <ul>
          {result.criteria_scores
            .filter((c) => c.score < c.max_score)
            .map((c) => (
              <li key={c.criterion}>
                <span className="revision-tag">{c.criterion}</span> {c.improvement}
              </li>
            ))}
          {result.criteria_scores.every((c) => c.score >= c.max_score) && <li>모든 항목이 만점입니다.</li>}
        </ul>
      </div>

      <details className="rationale-details">
        <summary>항목별 근거 전체 보기</summary>
        {result.criteria_scores.map((c) => (
          <div key={c.criterion} className="rationale-item">
            <strong>{c.criterion}</strong>
            <p>{c.rationale}</p>
          </div>
        ))}
      </details>
    </div>
  )
}

export function FeedbackTab({ result }) {
  if (!result) return <p className="muted">아직 첨삭 결과가 없습니다. 왼쪽에서 "문법/표현 첨삭"을 눌러주세요.</p>
  return (
    <div>
      {result.spelling_error && <div className="banner banner-warn">맞춤법 검사 실패: {result.spelling_error}</div>}
      {result.polish_error && <div className="banner banner-warn">윤문 제안 생성 실패: {result.polish_error}</div>}

      <strong>맞춤법 교정 ({result.spelling_corrections.length}건)</strong>
      {result.spelling_corrections.length === 0 && <p className="muted">교정할 항목이 없습니다.</p>}
      <ul>
        {result.spelling_corrections.map((c, i) => (
          <li key={i}>
            <s>{c.original}</s> → <strong>{c.revised}</strong>
            <span className="muted">
              {' '}
              ({c.category}: {c.comment})
            </span>
          </li>
        ))}
      </ul>

      <strong>윤문 제안 ({result.polish_suggestions.length}건)</strong>
      {result.polish_suggestions.length === 0 && <p className="muted">제안할 항목이 없습니다.</p>}
      <ul>
        {result.polish_suggestions.map((p, i) => (
          <li key={i}>
            <s>{p.original}</s> → <strong>{p.suggestion}</strong>
            <p className="muted">{p.reason}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}
