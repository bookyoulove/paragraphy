import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import ScoreCard from '../components/ScoreCard';
import { formatWrittenAt } from '../utils/formatters';

export default function AnswerDetailPage({ user, session, onLoad }) {
  const { sessionId, answerId } = useParams();
  const navigate = useNavigate();
  const isCurrentSession = String(session?.id) === sessionId;
  useEffect(() => {
    if (user && !isCurrentSession) onLoad(sessionId);
  }, [user, sessionId, isCurrentSession, onLoad]);
  if (!isCurrentSession) return <div className="panel-empty">세션을 불러오는 중입니다.</div>;

  const answer = session.answers.find((item) => item.id === answerId);
  if (!answer) return <div className="panel-empty">해당 답안을 찾을 수 없습니다.</div>;

  return (
    <div className="work-columns">
      <section className="column-slot">
        <section className="answer-box">
          <div className="answer-header">
            <div className="answer-title">{answer.name}</div>
            <div className="word-counter">{answer.userAnswer.trim().length}자</div>
          </div>
          <div className="label-sub">{formatWrittenAt(answer.createdAt)}</div>
          <div className="highlight-wrap">
            <textarea className="answer-input" value={answer.userAnswer} readOnly spellCheck="false" />
          </div>
          <div className="answer-actions">
            <button className="ghost-btn" onClick={() => navigate(`/history/${sessionId}`)}>
              답안 목록으로
            </button>
          </div>
        </section>
      </section>
      <section className="column-slot">
        <aside className="right-panel">
          {answer.result ? (
            <div className="tab-panels">
              <div className="tab-panel active">
                <ScoreCard result={answer.result} />
              </div>
            </div>
          ) : (
            <div className="panel-empty">아직 채점되지 않은 답안입니다.</div>
          )}
        </aside>
      </section>
    </div>
  );
}
