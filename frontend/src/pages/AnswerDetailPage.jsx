import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Workbench from '../components/Workbench';

export default function AnswerDetailPage({ user, session, onLoad, onSave, onGrade }) {
  const { sessionId, answerId } = useParams();
  const navigate = useNavigate();
  const isCurrentSession = String(session?.id) === sessionId;
  const loadAttemptRef = useRef(null);
  const loadKey = user ? `${user.identifier}:${sessionId}` : null;
  const [isEditing, setIsEditing] = useState(false);
  useEffect(() => {
    if (!user || isCurrentSession || loadAttemptRef.current === loadKey) return;
    loadAttemptRef.current = loadKey;
    onLoad(sessionId).catch(() => {});
  }, [user, sessionId, isCurrentSession, onLoad, loadKey]);
  useEffect(() => {
    setIsEditing(false);
  }, [answerId]);
  if (!isCurrentSession) return <div className="panel-empty">세션을 불러오는 중입니다.</div>;

  const answer = session.answers.find((item) => item.id === answerId);
  if (!answer) return <div className="panel-empty">해당 답안을 찾을 수 없습니다.</div>;

  const saveAsNextRound = (answerText, options) =>
    onSave(answerText, { ...options, createNew: true });
  const openSavedAnswer = (savedSession) => {
    if (savedSession?.answerId) {
      navigate(`/history/${sessionId}/answers/${savedSession.answerId}`, { replace: true });
    }
  };

  return (
    <Workbench
      problem={session.problem}
      session={session}
      answerOverride={answer}
      resultOverride={answer.result}
      onSave={isEditing ? saveAsNextRound : undefined}
      onSaveComplete={isEditing ? openSavedAnswer : undefined}
      onGrade={isEditing ? onGrade : undefined}
      onNewAnswer={() => navigate(`/sessions/${sessionId}`, { state: { startNew: true } })}
      onEditAnswer={() => setIsEditing(true)}
      readOnly={!isEditing}
      forceEdit={isEditing}
    />
  );
}
