import { useNavigate } from 'react-router-dom';
import HistoryView from '../components/HistoryView';

export default function HistoryPage({ sessions, onLoad }) {
  const navigate = useNavigate();
  const resumeSession = async (session) => { await onLoad(session.id); navigate(`/sessions/${session.id}`); };
  return <HistoryView sessions={sessions} onResume={resumeSession} />;
}
