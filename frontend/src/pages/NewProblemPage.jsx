import { useNavigate } from 'react-router-dom';
import CustomProblemForm from '../components/CustomProblemForm';

export default function NewProblemPage({ onGenerate, onCreate }) {
  const navigate = useNavigate();
  const createProblem = async (form) => {
    const session = await onCreate(form);
    navigate(`/sessions/${session.id}`);
  };
  return <CustomProblemForm onGenerate={onGenerate} onCreate={createProblem} />;
}
