import { useEffect, useRef } from 'react';
import { useLocation, useParams } from 'react-router-dom';
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
  const { sessionId } = useParams();
  const location = useLocation();
  const startNew = location.state?.startNew === true;
  const isCurrentSession = String(session?.id) === sessionId;
  const loadAttemptRef = useRef(null);
  const loadKey = user ? `${user.identifier}:${sessionId}` : null;
  useEffect(() => {
    if (!user || isCurrentSession || loadAttemptRef.current === loadKey) return;
    loadAttemptRef.current = loadKey;
    onLoad(sessionId).catch(() => {});
  }, [user, sessionId, isCurrentSession, onLoad, loadKey]);
  if (!isCurrentSession) return <div className="panel-empty">세션을 불러오는 중입니다.</div>;
  return (
    <Workbench
      problem={session.problem}
      session={session}
      onSave={onSave}
      onGrade={onGrade}
      onRename={onRename}
      onNewAnswerStateChange={onNewAnswerStateChange}
      startNew={startNew}
    />
  );
}
