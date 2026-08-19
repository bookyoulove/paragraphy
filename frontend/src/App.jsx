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
import { api } from './api/client';

export default function App() {
  const [entered, setEntered] = useState(false);
  const [user, setUser] = useState(null);
  const [view, setView] = useState('pick-existing');
  const [problems, setProblems] = useState([]);
  const [problem, setProblem] = useState(null);
  const [session, setSession] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState('');

  const reportError = (err) => {
    setError(err?.message || '알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
  };

  const refresh = async () => {
    try {
      setProblems(await api.getProblems());
      return true;
    } catch (err) {
      reportError(err);
      return false;
    }
  };

  useEffect(() => {
    if (!user) return;
    Promise.all([api.getProblems(), api.getSessions()])
      .then(([loadedProblems, loadedSessions]) => {
        setProblems(loadedProblems);
        setSessions(loadedSessions);
      })
      .catch(reportError);
  }, [user]);

  const select = async (next) => {
    try {
      const createdSession = await api.createSession(next);
      setProblem(createdSession.problem);
      setSession(createdSession);
      setView('work');
      return true;
    } catch (err) {
      reportError(err);
      return false;
    }
  };

  const save = async (answer) => {
    if (!session) return;
    const updated = await api.saveAnswer(session, answer);
    setSession(updated);
    setSessions(await api.getSessions());
    return updated;
  };

  const grade = async (sessionToGrade) => {
    if (!sessionToGrade) return;
    const updated = await api.grade(sessionToGrade);
    setSession({ ...sessionToGrade, results: [...sessionToGrade.results, updated] });
    setSessions(await api.getSessions());
  };

  const generateRubric = async (form) => {
    try {
      return await api.generateRubric(form);
    } catch (err) {
      reportError(err);
      throw err;
    }
  };

  const create = async (form) => {
    try {
      const created = await api.createProblem(form);
      if (!(await refresh())) return false;
      return select(created);
    } catch (err) {
      reportError(err);
      return false;
    }
  };
  if (!entered) return <Landing onStart={() => setEntered(true)} />;
  return (
    <>
      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError('')} aria-label="오류 메시지 닫기">
            닫기 ✕
          </button>
        </div>
      )}
      <div className="page-wrap">
        <header className="topbar">
          <Brand />
          <div className="topbar-right">
            <div className="topbar-meta">논술 채점 · 첨삭</div>
            {user && (
              <div className="topbar-user">
                <span>{user.identifier}</span>
                <button
                  className="ghost-btn dark"
                  onClick={() => {
                    api.clearToken();
                    setUser(null);
                    setProblem(null);
                    setSession(null);
                    setSessions([]);
                    setProblems([]);
                  }}
                >
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
              <span className="session-status">{session ? `세션 ${session.id} 진행 중` : ''}</span>
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
              <CustomProblemForm onGenerate={generateRubric} onCreate={create} />
            )}
            {view === 'work' && (
              <Workbench
                problem={problem}
                session={session}
                onSave={save}
                onGrade={grade}
                readOnly={Boolean(session?.results?.length)}
              />
            )}
            {view === 'history' && (
              <HistoryView
                sessions={sessions}
                onResume={(item) => {
                  api
                    .getSession(item.id)
                    .then((loaded) => {
                      setProblem(loaded.problem);
                      setSession(loaded);
                    })
                    .catch(reportError);
                  setView('work');
                }}
              />
            )}
            {view === 'compare' && (
              <HistoryView
                sessions={sessions}
                compareOnly
                onResume={(item) => {
                  api
                    .getSession(item.id)
                    .then((loaded) => {
                      setProblem(loaded.problem);
                      setSession(loaded);
                    })
                    .catch(reportError);
                  setView('work');
                }}
              />
            )}
          </main>
        </div>
      </div>
      {user && view === 'work' && session?.results.length > 0 && (
        <TutorChatModal session={session} onChat={api.chat} onLoadHistory={api.getChat} />
      )}
      {!user && (
        <LoginModal
          onLogin={async ({ username, password }) => setUser(await api.login(username, password))}
        />
      )}
    </>
  );
}
