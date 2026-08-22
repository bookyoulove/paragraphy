import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { formatWrittenAt } from '../utils/formatters';

export default function AnswerListPage({ user, session, onLoad, onDelete }) {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const isCurrentSession = String(session?.id) === sessionId;
  const [deletingId, setDeletingId] = useState(null);
  const loadAttemptRef = useRef(null);
  const loadKey = user ? `${user.identifier}:${sessionId}` : null;
  useEffect(() => {
    if (!user || isCurrentSession || loadAttemptRef.current === loadKey) return;
    loadAttemptRef.current = loadKey;
    onLoad(sessionId).catch(() => {});
  }, [user, sessionId, isCurrentSession, onLoad, loadKey]);
  if (!isCurrentSession) return <div className="panel-empty">세션을 불러오는 중입니다.</div>;

  const removeAnswer = async (answerId) => {
    if (!window.confirm('이 답안을 삭제할까요? 채점 결과와 대화 기록도 함께 삭제됩니다.')) return;
    setDeletingId(answerId);
    try {
      await onDelete(sessionId, answerId);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="picker-view">
      <div className="picker-view-header">
        <div>
          <div className="label-title">{session.problem.title}</div>
          <div className="label-sub">
            {session.problem.source} · 지금까지 작성한 답안 {session.answers.length}개
          </div>
        </div>
        <button className="primary-btn" onClick={() => navigate(`/sessions/${sessionId}`)}>
          이어서 답안 작성
        </button>
      </div>
      <div className="history-list">
        {session.answers.length ? (
          session.answers.map((item) => (
            <div className="history-card round-card" key={item.id}>
              <button
                className="history-card-main round-card-main"
                onClick={() => navigate(`/history/${sessionId}/answers/${item.id}`)}
              >
                <div className="history-card-title">{item.name}</div>
                <div className="history-card-meta">{formatWrittenAt(item.createdAt)}</div>
              </button>
              <span className={`history-card-score ${item.result ? '' : 'pending'}`}>
                {item.result ? `${item.result.score} / ${item.result.totalMax}` : '미채점'}
              </span>
              <button
                className="ghost-btn round-delete-btn"
                disabled={deletingId === item.id}
                onClick={() => removeAnswer(item.id)}
              >
                {deletingId === item.id ? '삭제 중...' : '답안 삭제'}
              </button>
            </div>
          ))
        ) : (
          <div className="panel-empty">아직 작성한 답안이 없습니다.</div>
        )}
      </div>
    </div>
  );
}
