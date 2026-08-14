import { useState } from 'react';

export default function ResultPanel({ result, results }) {
  const [tab, setTab] = useState('grade');
  const pct = result ? Math.round((result.score / result.totalMax) * 100) : 0;
  return (
    <aside className="right-panel">
      <div className="tabs">
        {[
          ['grade', '채점 결과'],
          ['proof', '첨삭 목록'],
        ].map(([id, label]) => (
          <button
            key={id}
            className={`tab ${tab === id ? 'active' : ''}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="tab-panels">
        <div className={`tab-panel ${tab === 'grade' ? 'active' : ''}`}>
          {!result ? (
            <div className="panel-empty">
              아직 채점 결과가 없습니다. 답안을 저장한 뒤 채점 요청을 눌러주세요.
            </div>
          ) : (
            <div className="score-card">
              <div className="score-ring-wrap">
                <div className="score-ring" style={{ '--score': pct }}>
                  <div className="score-inner">
                    <span className="score-number">{result.score}</span>
                    <span className="score-divider">/ {result.totalMax}</span>
                  </div>
                </div>
                <div className="score-text">
                  <div className="score-title">채점 기준 적용</div>
                  <div className="score-sub">{result.commentary}</div>
                </div>
              </div>
              <div className="criteria-list">
                {result.scores.map((item) => (
                  <div className="criteria-item" key={item.label}>
                    <div className="criteria-row">
                      <span>{item.label}</span>
                      <span>
                        {item.value} / {item.maxScore}
                      </span>
                    </div>
                    <div className="bar">
                      <span style={{ width: `${(item.value / item.maxScore) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="checklist-box">
                <div className="checklist-title">수정 방향성</div>
                <ul>
                  {result.suggestions.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              {results.length > 1 && (
                <div className="compare-section">
                  <div className="compare-title">채점 비교</div>
                  <div className="compare-table-wrap">
                    <table className="compare-table">
                      <thead>
                        <tr>
                          <th>회차</th>
                          {results.map((item) => (
                            <th key={item.attempt}>{item.attempt}회차</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        <tr className="compare-total">
                          <td>총점</td>
                          {results.map((item) => (
                            <td key={item.attempt}>
                              {item.score} / {item.totalMax}
                            </td>
                          ))}
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        <div className={`tab-panel ${tab === 'proof' ? 'active' : ''}`}>
          {!result ? (
            <div className="proof-box">
              <div className="proof-tag">정보</div>
              <div className="proof-text">채점 후 문법 및 첨삭 항목이 표시됩니다.</div>
            </div>
          ) : (
            <>
              <div className="proof-count">감지된 오류 {result.errors.length}건 · 샘플 첨삭</div>
              <div className="proof-list">
                {result.errors.map((item) => (
                  <div className="proof-box" key={item.before}>
                    <div className="proof-tag warning">{item.type}</div>
                    <div className="proof-text">
                      <del>{item.before}</del> → {item.after}
                    </div>
                    <div className="proof-meta">{item.note}</div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </aside>
  );
}
