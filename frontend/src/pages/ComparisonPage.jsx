import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import CompareTable from '../components/CompareTable';

export default function ComparisonPage({ user, session, onLoad }) {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const isCurrentSession = String(session?.id) === sessionId;
  useEffect(() => {
    if (user && !isCurrentSession) onLoad(sessionId);
  }, [user, sessionId, isCurrentSession, onLoad]);
  if (!isCurrentSession) return <div className="panel-empty">세션을 불러오는 중입니다.</div>;

  return (
    <div className="picker-view">
      <div className="picker-view-header">
        <div>
          <div className="label-title">{session.problem.title}</div>
          <div className="label-sub">{session.problem.source} · 채점 비교</div>
        </div>
      </div>
      {session.results.length > 1 ? (
        <CompareTable
          results={session.results}
          onSelectRound={(answerId) => navigate(`/history/${sessionId}/answers/${answerId}`)}
        />
      ) : (
        <div className="panel-empty">아직 2회 이상 채점된 답안이 없습니다.</div>
      )}
    </div>
  );
}
