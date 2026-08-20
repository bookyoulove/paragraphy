import { useCallback, useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useMatch, useNavigate } from 'react-router-dom';
import { api } from './api/client';
import Brand from './components/Brand';
import LoginModal from './components/LoginModal';
import Sidebar from './components/Sidebar';
import TutorChatModal from './components/TutorChatModal';
import useAppData from './hooks/useAppData';
import ComparePage from './pages/ComparePage';
import HistoryPage from './pages/HistoryPage';
import LandingPage from './pages/LandingPage';
import NewProblemPage from './pages/NewProblemPage';
import ProblemsPage from './pages/ProblemsPage';
import SessionPage from './pages/SessionPage';

function AppLayout({ user, setUser, data, actions, error, clearError }) {
  const navigate = useNavigate();
  const isSessionPage = useMatch('/sessions/:sessionId');
  const logout = () => {
    api.clearToken();
    actions.clear();
    setUser(null);
    navigate('/');
  };

  return (
    <>
      {error && <div className="error-banner" role="alert"><span>{error}</span><button type="button" onClick={clearError} aria-label="오류 메시지 닫기">닫기 ✕</button></div>}
      <div className="page-wrap">
        <header className="topbar">
          <Brand />
          <div className="topbar-right">
            <div className="topbar-meta">논술 채점 · 첨삭</div>
            {user && <div className="topbar-user"><span>{user.identifier}</span><button className="ghost-btn dark" onClick={logout}>전환</button></div>}
          </div>
        </header>
        <div className="app-shell">
          <Sidebar />
          <main className="main-content">
            <div className="content-info-bar">
              <span className="current-problem-label">{data.session?.problem ? `${data.session.problem.title} — ${data.session.problem.meta.school}` : '선택된 문제가 없습니다.'}</span>
              <span className="session-status">{data.session ? `세션 ${data.session.id} 진행 중` : ''}</span>
            </div>
            <Routes>
              <Route path="/problems" element={<ProblemsPage problems={data.problems} onRefresh={actions.refreshProblems} onSelect={actions.createSession} />} />
              <Route path="/problems/new" element={<NewProblemPage onGenerate={actions.generateRubric} onCreate={actions.createProblem} />} />
              <Route path="/sessions/:sessionId" element={<SessionPage user={user} session={data.session} onLoad={actions.loadSession} onSave={actions.saveAnswer} onGrade={actions.grade} />} />
              <Route path="/history" element={<HistoryPage sessions={data.sessions} onLoad={actions.loadSession} />} />
              <Route path="/compare" element={<ComparePage sessions={data.sessions} onLoad={actions.loadSession} />} />
              <Route path="*" element={<Navigate to="/problems" replace />} />
            </Routes>
          </main>
        </div>
      </div>
      {user && isSessionPage && data.session?.results.length > 0 && <TutorChatModal session={data.session} onChat={api.chat} onLoadHistory={api.getChat} />}
      {!user && <LoginModal onLogin={actions.login} />}
    </>
  );
}

function ParagraphyApp() {
  const [user, setUser] = useState(() => api.getStoredUser());
  const [error, setError] = useState('');
  const data = useAppData(user);
  useEffect(() => {
    const handleAuthExpired = () => {
      data.clear();
      setUser(null);
    };
    window.addEventListener('paragraphy:auth-expired', handleAuthExpired);
    return () => window.removeEventListener('paragraphy:auth-expired', handleAuthExpired);
  }, [data.clear]);
  const reportError = useCallback((err) => setError(err?.message || '알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'), []);
  const protect = useCallback((callback) => async (...args) => {
    try { return await callback(...args); } catch (err) { reportError(err); throw err; }
  }, [reportError]);
  const actions = {
    refreshProblems: protect(data.refreshProblems),
    createSession: protect(data.createSession),
    loadSession: protect(data.loadSession),
    saveAnswer: protect(data.saveAnswer),
    grade: protect(data.grade),
    createProblem: protect(data.createProblem),
    generateRubric: protect(api.generateRubric),
    clear: data.clear,
    login: protect(async ({ username, password }) => setUser(await api.login(username, password))),
  };

  return <Routes><Route path="/" element={<LandingPage />} /><Route path="/*" element={<AppLayout user={user} setUser={setUser} data={data} actions={actions} error={error} clearError={() => setError('')} />} /></Routes>;
}

export default function App() {
  return <BrowserRouter><ParagraphyApp /></BrowserRouter>;
}
