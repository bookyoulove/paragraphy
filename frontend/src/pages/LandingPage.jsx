import { useNavigate } from 'react-router-dom';
import Landing from '../components/Landing';

export default function LandingPage() {
  const navigate = useNavigate();
  return <Landing onStart={() => navigate('/problems')} />;
}
