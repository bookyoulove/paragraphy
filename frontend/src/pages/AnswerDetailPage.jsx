import { useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Workbench from '../components/Workbench';

export default function AnswerDetailPage({ user, session, onLoad }) {
  const { sessionId, answerId } = useParams();
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
