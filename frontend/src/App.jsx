import { useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useMatch, useNavigate } from 'react-router-dom';
import LoginModal from './components/LoginModal';
import Brand from './components/Brand';
import Sidebar from './components/Sidebar';
import TutorChatModal from './components/TutorChatModal';
import LandingPage from './pages/LandingPage';
import ProblemsPage from './pages/ProblemsPage';
import NewProblemPage from './pages/NewProblemPage';
import SessionPage from './pages/SessionPage';
import HistoryPage from './pages/HistoryPage';
import ComparePage from './pages/ComparePage';
import { api } from './api/client';
import useAppData from './hooks/useAppData';

function AppLayout({ user, setUser, problems, session, sessions, actions }) {
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
              <span className="current-problem-label">{session?.problem ? `${session.problem.title} — ${session.problem.meta.school}` : '선택된 문제가 없습니다.'}</span>
              <span className="session-status">{session ? `세션 ${session.id} 진행 중` : ''}</span>
            </div>
            <Routes>
              <Route path="/problems" element={<ProblemsPage problems={problems} onRefresh={actions.refresh} onSelect={actions.createSession} />} />
              <Route path="/problems/new" element={<NewProblemPage onGenerate={api.generateRubric} onCreate={actions.createProblem} />} />
              <Route path="/sessions/:sessionId" element={<SessionPage user={user} session={session} onLoad={actions.loadSession} onSave={actions.saveAnswer} onGrade={actions.grade} />} />
              <Route path="/history" element={<HistoryPage sessions={sessions} onLoad={actions.loadSession} />} />
              <Route path="/compare" element={<ComparePage sessions={sessions} onLoad={actions.loadSession} />} />
              <Route path="*" element={<Navigate to="/problems" replace />} />
            </Routes>
          </main>
        </div>
      </div>
      {user && isSessionPage && session?.results.length > 0 && <TutorChatModal session={session} onChat={api.chat} onLoadHistory={api.getChat} />}
      {!user && <LoginModal onLogin={async ({ username, password }) => setUser(await api.login(username, password))} />}
    </>
  );
}

function ParagraphyApp() {
  const [user, setUser] = useState(null);
  const data = useAppData(user);
  const actions = {
    refresh: data.refreshProblems,
    createSession: data.createSession,
    loadSession: data.loadSession,
    saveAnswer: data.saveAnswer,
    grade: data.grade,
    createProblem: data.createProblem,
    clear: data.clear,
  };

  return <Routes><Route path="/" element={<LandingPage />} /><Route path="/*" element={<AppLayout user={user} setUser={setUser} problems={data.problems} session={data.session} sessions={data.sessions} actions={actions} />} /></Routes>;
}

export default function App() {
  return <BrowserRouter><ParagraphyApp /></BrowserRouter>;
}
