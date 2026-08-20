import { useCallback, useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useMatch, useNavigate } from 'react-router-dom';
import { api } from './api/client';
import Brand from './components/Brand';
import LoginModal from './components/LoginModal';
import Sidebar from './components/Sidebar';
import TutorChatModal from './components/TutorChatModal';
import useAppData from './hooks/useAppData';
import AnswerDetailPage from './pages/AnswerDetailPage';
import AnswerListPage from './pages/AnswerListPage';
import ComparePage from './pages/ComparePage';
import ComparisonPage from './pages/ComparisonPage';
import HistoryPage from './pages/HistoryPage';
import LandingPage from './pages/LandingPage';
import ProblemsPage from './pages/ProblemsPage';
import SessionPage from './pages/SessionPage';
import WeeklyReportDetailPage from './pages/WeeklyReportDetailPage';
import WeeklyReportsPage from './pages/WeeklyReportsPage';

function AppLayout({ user, setUser, data, actions, error, clearError }) {
  const navigate = useNavigate();
  const isSessionPage = useMatch('/sessions/:sessionId');
  const isProblemsPage = useMatch('/problems');
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
              {!isProblemsPage && (
                <button className="ghost-btn content-info-action" onClick={() => navigate('/problems')}>
                  문제 선택하러 가기
                </button>
              )}
            </div>
            <Routes>
              <Route path="/problems" element={<ProblemsPage problems={data.problems} onRefresh={actions.refreshProblems} onSelect={actions.createSession} onGenerate={actions.generateRubric} onCreate={actions.createProblem} onDeleteProblem={actions.deleteProblem} onRecommend={actions.recommendProblems} />} />
              <Route path="/sessions/:sessionId" element={<SessionPage user={user} session={data.session} onLoad={actions.loadSession} onSave={actions.saveAnswer} onGrade={actions.grade} onRename={actions.renameAnswer} />} />
              <Route path="/history" element={<HistoryPage sessions={data.sessions} onDelete={actions.deleteSession} />} />
              <Route path="/history/:sessionId" element={<AnswerListPage user={user} session={data.session} onLoad={actions.loadSession} onDelete={actions.deleteAnswer} />} />
              <Route path="/history/:sessionId/answers/:answerId" element={<AnswerDetailPage user={user} session={data.session} onLoad={actions.loadSession} />} />
              <Route path="/compare" element={<ComparePage sessions={data.sessions} />} />
              <Route path="/compare/:sessionId" element={<ComparisonPage user={user} session={data.session} onLoad={actions.loadSession} />} />
              <Route path="/weekly-reports" element={<WeeklyReportsPage user={user} />} />
              <Route path="/weekly-reports/:reportId" element={<WeeklyReportDetailPage user={user} onRefreshProblems={actions.refreshProblems} />} />
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
    renameAnswer: protect(data.renameAnswer),
    deleteAnswer: protect(data.deleteAnswer),
    deleteSession: protect(data.deleteSession),
    createProblem: protect(data.createProblem),
    deleteProblem: protect(data.deleteProblem),
    generateRubric: protect(api.generateRubric),
    recommendProblems: protect(api.recommendProblems),
    clear: data.clear,
    login: protect(async ({ username, password }) => setUser(await api.login(username, password))),
  };

  return <Routes><Route path="/" element={<LandingPage />} /><Route path="/*" element={<AppLayout user={user} setUser={setUser} data={data} actions={actions} error={error} clearError={() => setError('')} />} /></Routes>;
}

export default function App() {
  return <BrowserRouter basename={import.meta.env.BASE_URL}><ParagraphyApp /></BrowserRouter>;
}
