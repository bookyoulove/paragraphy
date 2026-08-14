import { useEffect, useState } from 'react';
import Landing from './components/Landing';
import LoginModal from './components/LoginModal';
import Brand from './components/Brand';
import Sidebar from './components/Sidebar';
import ProblemPicker from './components/ProblemPicker';
import CustomProblemForm from './components/CustomProblemForm';
import Workbench from './components/Workbench';
import HistoryView from './components/HistoryView';
import TutorChatModal from './components/TutorChatModal';
import { mockApi } from './mocks/api';

export default function App() {
  const [entered, setEntered] = useState(false);
  const [user, setUser] = useState(null);
  const [view, setView] = useState('pick-existing');
  const [problems, setProblems] = useState([]);
  const [problem, setProblem] = useState(null);
  const [session, setSession] = useState(null);
  const [sessions, setSessions] = useState([]);
  const refresh = async () => setProblems(await mockApi.getProblems());
  useEffect(() => {
    refresh();
  }, []);
  const select = async (next) => {
    setProblem(next);
    setSession(await mockApi.createSession(next));
    setView('work');
  };
  const save = async (answer) => {
    if (!session) return;
    const updated = await mockApi.saveAnswer(session, answer);
    setSession({ ...updated });
    setSessions(await mockApi.getSessions());
  };
  const grade = async () => {
    if (!session) return;
    const updated = await mockApi.grade(session);
    setSession((old) => ({ ...old, results: [...old.results.slice(0, -1), updated] }));
    setSessions(await mockApi.getSessions());
  };
  const create = async (form) => {
    const created = await mockApi.createProblem(form);
    await refresh();
    await select(created);
  };
  if (!entered) return <Landing onStart={() => setEntered(true)} />;
  return (
    <>
      <div className="page-wrap">
        <header className="topbar">
          <Brand />
          <div className="topbar-right">
            <div className="topbar-meta">논술 채점 · 첨삭 · 샘플 모드</div>
            {user && (
              <div className="topbar-user">
                <span>{user.identifier}</span>
                <button className="ghost-btn dark" onClick={() => setUser(null)}>
                  전환
                </button>
              </div>
            )}
          </div>
        </header>
        <div className="app-shell">
          <Sidebar active={view} onChange={setView} />
          <main className="main-content">
            <div className="content-info-bar">
              <span className="current-problem-label">
                {problem ? `${problem.title} — ${problem.meta.school}` : '선택된 문제가 없습니다.'}
              </span>
              <span className="session-status">
                {session ? `샘플 세션 ${session.id} 진행 중` : ''}
              </span>
            </div>
            {view === 'pick-existing' && (
              <ProblemPicker
                problems={problems}
                selectedId={problem?.id}
                onSelect={select}
                onRefresh={refresh}
              />
            )}
            {view === 'pick-custom' && (
              <CustomProblemForm onGenerate={mockApi.generateRubric} onCreate={create} />
            )}
            {view === 'work' && (
              <Workbench problem={problem} session={session} onSave={save} onGrade={grade} />
            )}
            {view === 'history' && (
              <HistoryView
                sessions={sessions}
                onResume={(item) => {
                  setProblem(item.problem);
                  setSession(item);
                  setView('work');
                }}
              />
            )}
            {view === 'compare' && (
              <HistoryView
                sessions={sessions}
                compareOnly
                onResume={(item) => {
                  setProblem(item.problem);
                  setSession(item);
                  setView('work');
                }}
              />
            )}
          </main>
        </div>
      </div>
      {user && view === 'work' && session?.results.length > 0 && (
        <TutorChatModal session={session} onChat={mockApi.chat} />
      )}
      {!user && <LoginModal onLogin={setUser} />}
    </>
  );
}
