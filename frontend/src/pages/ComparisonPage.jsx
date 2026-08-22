import { useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import CompareTable from '../components/CompareTable';
import ComparisonChart from '../components/ComparisonChart';
import { COMPARISON_ITEM_WIDTH, COMPARISON_LABEL_WIDTH } from '../utils/comparisonData';

export default function ComparisonPage({ user, session, onLoad }) {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const isCurrentSession = String(session?.id) === sessionId;
  const loadAttemptRef = useRef(null);
  const loadKey = user ? `${user.identifier}:${sessionId}` : null;
  useEffect(() => {
    if (!user || isCurrentSession || loadAttemptRef.current === loadKey) return;
    loadAttemptRef.current = loadKey;
    onLoad(sessionId).catch(() => {});
  }, [user, sessionId, isCurrentSession, onLoad, loadKey]);
  if (!isCurrentSession) return <div className="panel-empty">세션을 불러오는 중입니다.</div>;

  const comparisonContentWidth =
    COMPARISON_LABEL_WIDTH + COMPARISON_ITEM_WIDTH * session.results.length;

  return (
    <div className="picker-view">
      <div className="picker-view-header">
        <div>
          <div className="label-title">{session.problem.title}</div>
          <div className="label-sub">{session.problem.source} · 채점 비교</div>
        </div>
      </div>
      {session.results.length > 1 ? (
        <div
          className="comparison-scroll"
          style={{ '--comparison-content-width': `${comparisonContentWidth}px` }}
        >
          <div className="comparison-scroll-content">
            <ComparisonChart results={session.results} truncate={false} />
            <CompareTable
              results={session.results}
              truncate={false}
              onSelectRound={(answerId) => navigate(`/history/${sessionId}/answers/${answerId}`)}
            />
          </div>
        </div>
      ) : (
        <div className="panel-empty">아직 2회 이상 채점된 답안이 없습니다.</div>
      )}
    </div>
  );
}
