import { useState } from 'react';

export default function HistoryView({ sessions, compareOnly, onResume, onDelete }) {
  const [deletingId, setDeletingId] = useState(null);
  const list = compareOnly ? sessions.filter((session) => session.results.length >= 2) : sessions;
  const message = compareOnly
    ? '아직 2회 이상 채점된 문제가 없습니다.'
    : '아직 작성한 답안이 없습니다. 문제를 선택해 답안을 작성해보세요.';

  const removeSession = async (event, sessionId) => {
    event.stopPropagation();
    if (!window.confirm('이 문제의 답안을 모두 삭제할까요? 채점 결과와 대화 기록도 함께 삭제됩니다.')) return;
    setDeletingId(sessionId);
    try {
      await onDelete(sessionId);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="picker-view">
      <div className="picker-view-header">
        <div>
          <div className="label-title">{compareOnly ? '채점 비교' : '답안 기록'}</div>
          <div className="label-sub">
            {compareOnly
              ? '2회 이상 채점한 문제를 확인합니다.'
              : '작성한 답안을 다시 열어 이어서 수정하고 재채점할 수 있습니다.'}
          </div>
        </div>
      </div>
      <div className="history-list">
        {list.length ? (
          list.map((session) => {
            const result = session.results.at(-1);
            return (
              <div className="history-card round-card" key={session.id}>
                <button className="history-card-main round-card-main" onClick={() => onResume(session)}>
                  <div className="history-card-title">{session.problem.title}</div>
                  <div className="history-card-meta">
                    {session.problem.source} · 답안 {session.answers.length}개
                  </div>
                </button>
                <span className={`history-card-score ${result ? '' : 'pending'}`}>
                  {result ? `${result.score} / ${result.totalMax}` : '미채점'}
                </span>
                {onDelete && (
                  <button
                    className="ghost-btn round-delete-btn"
                    disabled={deletingId === session.id}
                    onClick={(event) => removeSession(event, session.id)}
                  >
                    {deletingId === session.id ? '삭제 중...' : '답안 삭제'}
                  </button>
                )}
              </div>
            );
          })
        ) : (
          <div className="panel-empty">{message}</div>
        )}
      </div>
    </div>
  );
}
