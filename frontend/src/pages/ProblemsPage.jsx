import { useNavigate } from 'react-router-dom';
import ProblemPicker from '../components/ProblemPicker';

export default function ProblemsPage({ problems, onRefresh, onSelect }) {
  const navigate = useNavigate();
  const selectProblem = async (problem) => {
    const session = await onSelect(problem);
    navigate(`/sessions/${session.id}`);
  };
  return <ProblemPicker problems={problems} onSelect={selectProblem} onRefresh={onRefresh} />;
}
