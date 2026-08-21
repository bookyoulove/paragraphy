import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Workbench from '../components/Workbench';

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
    <Workbench
      problem={session.problem}
      session={session}
      answerOverride={answer}
      resultOverride={answer.result}
      onNewAnswer={() => navigate(`/sessions/${sessionId}`, { state: { startNew: true } })}
      onEditAnswer={() => navigate(`/sessions/${sessionId}`)}
      readOnly
    />
  );
}
