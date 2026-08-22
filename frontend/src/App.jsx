import { useCallback, useEffect, useRef, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useMatch, useNavigate } from 'react-router-dom';
import { api } from './api/client';
import AgentProgress from './components/AgentProgress';
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

const ERROR_DISMISS_SECONDS = 8;

function AppLayout({
  user,
  setUser,
  data,
  actions,
  error,
  errorRemaining,
  errorProgress,
  clearError,
  agentTask,
}) {
  const navigate = useNavigate();
  const [isWritingNewAnswer, setIsWritingNewAnswer] = useState(false);
  const isSessionPage = useMatch('/sessions/:sessionId');
  const historyAnswerMatch = useMatch('/history/:sessionId/answers/:answerId');
  const isProblemsPage = useMatch('/problems');
  const historyAnswer =
    historyAnswerMatch && String(data.session?.id) === historyAnswerMatch.params.sessionId
      ? data.session?.answers?.find((item) => item.id === historyAnswerMatch.params.answerId)
      : null;
  const tutorResult = historyAnswerMatch
    ? historyAnswer?.result
    : isSessionPage && !isWritingNewAnswer && data.session?.answerSubmitted
      ? data.session.results.at(-1)
      : null;
  const logout = () => {
    api.clearToken();
    actions.clear();
    setUser(null);
    navigate('/problems');
  };

  return (
    <>
      {error && (
        <div className="error-banner" role="alert">
          <div className="error-banner-row">
            <span className="error-banner-message">{error}</span>
            <span className="error-banner-countdown" aria-live="polite">
              {errorRemaining}초 후 자동으로 사라집니다.
            </span>
            <button type="button" onClick={clearError} aria-label="오류 메시지 닫기">
              닫기 ✕
            </button>
          </div>
          <div
            className="error-banner-progress"
            role="progressbar"
            aria-label="오류 메시지 자동 닫힘까지 남은 시간"
            aria-valuemin="0"
            aria-valuemax={ERROR_DISMISS_SECONDS}
            aria-valuenow={errorRemaining}
          >
            <div className="error-banner-progress-value" style={{ width: `${errorProgress}%` }} />
          </div>
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
                <button className="ghost-btn dark" onClick={logout}>
                  전환
                </button>
              </div>
            )}
          </div>
        </header>
        <AgentProgress task={agentTask} />
        <div className="app-shell">
          <Sidebar />
          <main className="main-content">
            <div className="content-info-bar">
              <span className="current-problem-label">
                {data.session?.problem
                  ? `${data.session.problem.title} — ${data.session.problem.meta.school}`
                  : '선택된 문제가 없습니다.'}
              </span>
              {!isProblemsPage && (
                <button
                  className="ghost-btn content-info-action"
                  onClick={() => navigate('/problems')}
                >
                  문제 선택하러 가기
                </button>
              )}
            </div>
            <Routes>
              <Route
                path="/problems"
                element={
                  <ProblemsPage
                    problems={data.problems}
                    onRefresh={actions.refreshProblems}
                    onSelect={actions.createSession}
                    onGenerate={actions.generateRubric}
                    onCreate={actions.createProblem}
                    onDeleteProblem={actions.deleteProblem}
                    onRecommend={actions.recommendProblems}
                  />
                }
              />
              <Route
                path="/sessions/:sessionId"
                element={
                  <SessionPage
                    user={user}
                    session={data.session}
                    onLoad={actions.loadSession}
                    onSave={actions.saveAnswer}
                    onGrade={actions.grade}
                    onRename={actions.renameAnswer}
                    onNewAnswerStateChange={setIsWritingNewAnswer}
                  />
                }
              />
              <Route
                path="/history"
                element={<HistoryPage sessions={data.sessions} onDelete={actions.deleteSession} />}
              />
              <Route
                path="/history/:sessionId"
                element={
                  <AnswerListPage
                    user={user}
                    session={data.session}
                    onLoad={actions.loadSession}
                    onDelete={actions.deleteAnswer}
                  />
                }
              />
              <Route
                path="/history/:sessionId/answers/:answerId"
                element={
                  <AnswerDetailPage
                    user={user}
                    session={data.session}
                    onLoad={actions.loadSession}
                  />
                }
              />
              <Route path="/compare" element={<ComparePage sessions={data.sessions} />} />
              <Route
                path="/compare/:sessionId"
                element={
                  <ComparisonPage user={user} session={data.session} onLoad={actions.loadSession} />
                }
              />
              <Route
                path="/weekly-reports"
                element={
                  <WeeklyReportsPage user={user} onCreateReport={actions.createWeeklySkillReport} />
                }
              />
              <Route
                path="/weekly-reports/:reportId"
                element={
                  <WeeklyReportDetailPage
                    user={user}
                    onRefreshProblems={actions.refreshProblems}
                    onGenerateProblem={actions.generateProblemFromReport}
                  />
                }
              />
              <Route path="*" element={<Navigate to="/problems" replace />} />
            </Routes>
          </main>
        </div>
      </div>
      {user && tutorResult && <TutorChatModal session={data.session} result={tutorResult} />}
      {!user && <LoginModal onLogin={actions.login} />}
    </>
  );
}

function ParagraphyApp() {
  const [user, setUser] = useState(() => api.getStoredUser());
  const [error, setError] = useState('');
  const [errorRemaining, setErrorRemaining] = useState(0);
  const [errorProgress, setErrorProgress] = useState(0);
  const [errorDismissAt, setErrorDismissAt] = useState(null);
  const [agentTask, setAgentTask] = useState(null);
  const agentTaskId = useRef(0);
  const data = useAppData(user);
  useEffect(() => {
    const handleAuthExpired = () => {
      data.clear();
      setUser(null);
    };
    window.addEventListener('paragraphy:auth-expired', handleAuthExpired);
    return () => window.removeEventListener('paragraphy:auth-expired', handleAuthExpired);
  }, [data.clear]);
  const clearError = useCallback(() => {
    setError('');
    setErrorRemaining(0);
    setErrorProgress(0);
    setErrorDismissAt(null);
  }, []);
  const reportError = useCallback((err) => {
    setError(err?.message || '알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    setErrorRemaining(ERROR_DISMISS_SECONDS);
    setErrorProgress(100);
    setErrorDismissAt(Date.now() + ERROR_DISMISS_SECONDS * 1000);
  }, []);
  useEffect(() => {
    if (!error || errorDismissAt === null) return undefined;

    const updateRemaining = () => {
      const millisecondsRemaining = Math.max(0, errorDismissAt - Date.now());
      const remaining = Math.ceil(millisecondsRemaining / 1000);
      setErrorRemaining(remaining);
      setErrorProgress((millisecondsRemaining / (ERROR_DISMISS_SECONDS * 1000)) * 100);
      if (remaining === 0) {
        setError('');
        setErrorDismissAt(null);
      }
    };

    updateRemaining();
    const timer = window.setInterval(updateRemaining, 50);
    return () => window.clearInterval(timer);
  }, [error, errorDismissAt]);
  const protect = useCallback(
    (callback) =>
      async (...args) => {
        try {
          return await callback(...args);
        } catch (err) {
          reportError(err);
          throw err;
        }
      },
    [reportError],
  );
  const runAgentTask = useCallback(async (label, callback) => {
    const id = ++agentTaskId.current;
    setAgentTask({ id, label, startedAt: Date.now() });
    try {
      return await callback();
    } finally {
      setAgentTask((current) => (current?.id === id ? null : current));
    }
  }, []);
  const trackAgent = useCallback(
    (label, callback) =>
      (...args) =>
        runAgentTask(label, () => callback(...args)),
    [runAgentTask],
  );
  const actions = {
    refreshProblems: protect(data.refreshProblems),
    createSession: protect(data.createSession),
    loadSession: protect(data.loadSession),
    saveAnswer: protect(data.saveAnswer),
    grade: trackAgent('채점', protect(data.grade)),
    renameAnswer: protect(data.renameAnswer),
    deleteAnswer: protect(data.deleteAnswer),
    deleteSession: protect(data.deleteSession),
    createProblem: protect(data.createProblem),
    deleteProblem: protect(data.deleteProblem),
    generateRubric: trackAgent('채점 기준 생성', protect(api.generateRubric)),
    recommendProblems: trackAgent('문제 추천·생성', protect(api.recommendProblems)),
    createWeeklySkillReport: trackAgent('주간 리포트 분석', protect(api.createWeeklySkillReport)),
    generateProblemFromReport: trackAgent(
      'AI 맞춤 문제 생성',
      protect(api.generateProblemFromReport),
    ),
    clear: data.clear,
    login: protect(async ({ username, password }) => setUser(await api.login(username, password))),
  };

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route
        path="/*"
        element={
          <AppLayout
            user={user}
            setUser={setUser}
            data={data}
            actions={actions}
            error={error}
            errorRemaining={errorRemaining}
            errorProgress={errorProgress}
            clearError={clearError}
            agentTask={agentTask}
          />
        }
      />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <ParagraphyApp />
    </BrowserRouter>
  );
}
