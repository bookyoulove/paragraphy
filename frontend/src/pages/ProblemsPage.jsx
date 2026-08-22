import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import CustomProblemForm from '../components/CustomProblemForm';
import ProblemPicker from '../components/ProblemPicker';

export default function ProblemsPage({
  problems,
  onRefresh,
  onSelect,
  onGenerate,
  onCreate,
  onDeleteProblem,
  onRecommend,
}) {
  const [tab, setTab] = useState('pick');
  const navigate = useNavigate();
  const selectProblem = async (problem) => {
    const session = await onSelect(problem);
    navigate(`/sessions/${session.id}`, { state: { startNew: true } });
  };
  const createProblem = async (form) => {
    const session = await onCreate(form);
    navigate(`/sessions/${session.id}`);
  };
  return (
    <div className="page-tabs">
      <div className="tabs page-tabs-bar">
        {[
          ['pick', '문제 선택'],
          ['custom', '문제 직접 입력'],
        ].map(([id, label]) => (
          <button
            key={id}
            className={`tab ${tab === id ? 'active' : ''}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === 'pick' ? (
        <ProblemPicker
          problems={problems}
          onSelect={selectProblem}
          onRefresh={onRefresh}
          onDelete={onDeleteProblem}
        />
      ) : (
        <CustomProblemForm
          myProblems={problems.filter((problem) => problem.raw.created_by_user)}
          onGenerate={onGenerate}
          onCreate={createProblem}
          onSelectExisting={selectProblem}
          onDeleteProblem={onDeleteProblem}
          onRecommend={onRecommend}
        />
      )}
    </div>
  );
}
