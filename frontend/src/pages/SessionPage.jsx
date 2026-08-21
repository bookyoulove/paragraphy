import { useEffect } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import Workbench from '../components/Workbench';

export default function SessionPage({
  user,
  session,
  onLoad,
  onSave,
  onGrade,
  onRename,
  onNewAnswerStateChange,
}) {
  const { sessionId, answerId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const startNew = location.state?.startNew === true;
  const isCurrentSession = String(session?.id) === sessionId;
  useEffect(() => {
    if (user && !isCurrentSession) onLoad(sessionId);
  }, [user, sessionId, isCurrentSession, onLoad]);
  if (!isCurrentSession) return <div className="panel-empty">세션을 불러오는 중입니다.</div>;

  const selectedAnswer = answerId
    ? session.answers.find((item) => String(item.id) === answerId)
    : null;
  if (answerId && !selectedAnswer)
    return <div className="panel-empty">해당 답안을 찾을 수 없습니다.</div>;

  return (
    <Workbench
      problem={session.problem}
      session={session}
      onSave={onSave}
      onGrade={onGrade}
      onRename={onRename}
      onNewAnswerStateChange={onNewAnswerStateChange}
      startNew={startNew}
      answerOverride={selectedAnswer}
      resultOverride={selectedAnswer?.result}
      readOnly={Boolean(selectedAnswer)}
      onNewAnswer={() => navigate(`/sessions/${sessionId}`, { state: { startNew: true } })}
      onEditAnswer={() => navigate(`/sessions/${sessionId}`)}
    />
  );
}
