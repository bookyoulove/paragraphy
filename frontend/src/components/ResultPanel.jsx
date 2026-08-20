import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import CompareTable from './CompareTable';
import ScoreCard from './ScoreCard';

export default function ResultPanel({ sessionId, result, results }) {
  const [tab, setTab] = useState('grade');
  const navigate = useNavigate();
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
            <>
              <ScoreCard result={result} />
              {results.length > 1 && (
                <div className="compare-section">
                  <div className="compare-title">채점 비교</div>
                  <CompareTable
                    results={results}
                    onSelectRound={(answerId) =>
                      navigate(`/history/${sessionId}/answers/${answerId}`)
                    }
                  />
                </div>
              )}
            </>
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
