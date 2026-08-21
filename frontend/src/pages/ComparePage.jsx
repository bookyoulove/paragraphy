import { useNavigate } from 'react-router-dom';
import HistoryView from '../components/HistoryView';

export default function ComparePage({ sessions }) {
  const navigate = useNavigate();
  const openComparison = (session) => navigate(`/compare/${session.id}`);
  return <HistoryView sessions={sessions} compareOnly onResume={openComparison} />;
}
