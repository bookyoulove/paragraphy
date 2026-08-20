import { useNavigate } from 'react-router-dom';
import HistoryView from '../components/HistoryView';

export default function HistoryPage({ sessions, onDelete }) {
  const navigate = useNavigate();
  const openSession = (session) => navigate(`/history/${session.id}`);
  return <HistoryView sessions={sessions} onResume={openSession} onDelete={onDelete} />;
}
