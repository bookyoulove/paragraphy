<<<<<<< HEAD
import { useEffect, useState } from 'react'
import { api } from './api'
import RubricSection from './components/RubricSection.jsx'
import { GradingTab, FeedbackTab } from './components/ResultPanel.jsx'
import ChatPanel from './components/ChatPanel.jsx'
import HistoryView from './components/HistoryView.jsx'

const EMPTY_RUBRIC = []
const TABS = [
  { key: 'grading', label: '채점 결과' },
  { key: 'feedback', label: '첨삭 목록' },
  { key: 'chat', label: 'Tutor Chat' },
]

export default function App() {
  const [userIdentifier, setUserIdentifier] = useState('demo-user')
  const [showHistory, setShowHistory] = useState(false)
  const [activeTab, setActiveTab] = useState('grading')

  const [mode, setMode] = useState('bank') // 'bank' | 'custom'
  const [problems, setProblems] = useState([])
  const [selectedProblemId, setSelectedProblemId] = useState('')
  const [selectedProblem, setSelectedProblem] = useState(null)

  const [customContent, setCustomContent] = useState('')
  const [customModelAnswer, setCustomModelAnswer] = useState('')
  const [customRubric, setCustomRubric] = useState(EMPTY_RUBRIC)
  const [suggesting, setSuggesting] = useState(false)

  const [essayText, setEssayText] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [gradingResult, setGradingResult] = useState(null)
  const [feedbackResult, setFeedbackResult] = useState(null)
  const [grading, setGrading] = useState(false)
  const [givingFeedback, setGivingFeedback] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.listProblems().then(setProblems).catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    if (mode !== 'bank' || !selectedProblemId) {
      setSelectedProblem(null)
      return
    }
    api.getProblem(selectedProblemId).then(setSelectedProblem).catch((e) => setError(e.message))
  }, [mode, selectedProblemId])

  // 문제/모드가 바뀌면 이전 채점 흐름(세션/결과)은 리셋 — 다른 문제로 이어서 채점하면 안 됨
  useEffect(() => {
    setSessionId(null)
    setGradingResult(null)
    setFeedbackResult(null)
    setActiveTab('grading')
  }, [mode, selectedProblemId])

  const problemMetaLabel =
    mode === 'bank' && selectedProblem
      ? `${selectedProblem.university || '기타'}${selectedProblem.year ? ` ${selectedProblem.year}` : ''}`
      : mode === 'custom'
        ? '직접 입력'
        : ''

  const handleSuggestRubric = async () => {
    if (!customContent.trim()) {
      setError('문제 내용을 먼저 입력하세요.')
      return
    }
    setSuggesting(true)
    setError('')
    try {
      const res = await api.suggestRubric({ content: customContent, model_answer: customModelAnswer || null })
      if (res.error) throw new Error(res.error)
      setCustomRubric(res.rubrics)
    } catch (e) {
      setError(e.message)
    } finally {
      setSuggesting(false)
    }
  }

  const handleGrade = async () => {
    if (!essayText.trim()) {
      setError('답안을 입력하세요.')
      return
    }
    setError('')
    setGrading(true)
    try {
      const payload = {
        user_identifier: userIdentifier,
        user_answer: essayText,
        session_id: sessionId,
      }
      if (mode === 'bank') {
        if (!selectedProblemId) throw new Error('문제를 선택하세요.')
        payload.problem_id = selectedProblemId
      } else {
        if (!customContent.trim()) throw new Error('문제 내용을 입력하세요.')
        if (customRubric.length === 0) throw new Error('채점 기준을 최소 1개 이상 입력하세요 (AI 제안을 받거나 직접 추가).')
        payload.problem_content = customContent
        payload.model_answer = customModelAnswer || null
        payload.rubric_items = customRubric.map((r) => ({ criteria: r.criteria, description: r.description, max_score: 5 }))
      }
      const res = await api.grade(payload)
      setGradingResult(res)
      setSessionId(res.session_id)
      setFeedbackResult(null)
      setActiveTab('grading')
    } catch (e) {
      setError(e.message)
    } finally {
      setGrading(false)
    }
  }

  const handleFeedback = async () => {
    if (!essayText.trim()) {
      setError('답안을 입력하세요.')
      return
    }
    setError('')
    setGivingFeedback(true)
    try {
      const res = await api.feedback({ essay_text: essayText, answer_id: gradingResult?.answer_id || null })
      setFeedbackResult(res)
      setActiveTab('feedback')
    } catch (e) {
      setError(e.message)
    } finally {
      setGivingFeedback(false)
    }
  }
=======
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
>>>>>>> 4c595276dbabe182f82a716684de89f60fec15ee

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
<<<<<<< HEAD
        </div>
        <div className="app-header-right">
          {problemMetaLabel && <span className="pill">{problemMetaLabel}</span>}
          <label className="user-field">
            <input value={userIdentifier} onChange={(e) => setUserIdentifier(e.target.value)} />
          </label>
          <button type="button" onClick={() => setShowHistory(true)}>
            지난 세션
          </button>
        </div>
      </header>

      {error && <div className="banner banner-error">{error}</div>}

      <main className="app-grid-3col">
        <section className="panel problem-panel">
          <div className="section-head">
            <h2>논술 문항</h2>
          </div>

          <div className="mode-toggle">
            <button type="button" className={mode === 'bank' ? 'active' : ''} onClick={() => setMode('bank')}>
              문제은행에서 선택
            </button>
            <button type="button" className={mode === 'custom' ? 'active' : ''} onClick={() => setMode('custom')}>
              직접 입력
            </button>
          </div>

          <div className="problem-scroll-area">
            {mode === 'bank' ? (
              <>
                <select value={selectedProblemId} onChange={(e) => setSelectedProblemId(e.target.value)}>
                  <option value="">-- 문제 선택 --</option>
                  {problems.map((p) => (
                    <option key={p.problem_id} value={p.problem_id}>
                      [{p.university || '기타'}
                      {p.year ? ` ${p.year}` : ''}] {p.title}
                    </option>
                  ))}
                </select>
                {selectedProblem && (
                  <>
                    <div className="problem-content">{selectedProblem.content}</div>
                    <RubricSection items={selectedProblem.rubrics} editable={false} onChange={() => {}} />
                  </>
                )}
              </>
            ) : (
              <>
                <textarea
                  className="problem-input"
                  placeholder="문제(및 지문)를 입력하세요"
                  value={customContent}
                  onChange={(e) => setCustomContent(e.target.value)}
                />
                <textarea
                  className="model-answer-input"
                  placeholder="모범답안 (선택)"
                  value={customModelAnswer}
                  onChange={(e) => setCustomModelAnswer(e.target.value)}
                />
                <RubricSection
                  items={customRubric}
                  editable
                  onChange={setCustomRubric}
                  onSuggest={handleSuggestRubric}
                  suggesting={suggesting}
                />
              </>
            )}
          </div>
        </section>

        <section className="panel answer-panel">
          <div className="section-head">
            <h2>답안 작성</h2>
            <span className="muted">{essayText.length}자</span>
          </div>
          <textarea
            className="answer-input"
            placeholder="학생 답안을 입력하세요"
            value={essayText}
            onChange={(e) => setEssayText(e.target.value)}
          />
          <div className="action-row">
            <button type="button" onClick={handleGrade} disabled={grading}>
              {grading ? '채점 중…' : sessionId ? '재채점 (다음 차수)' : '채점 요청'}
            </button>
            <button type="button" onClick={handleFeedback} disabled={givingFeedback}>
              {givingFeedback ? '첨삭 중…' : '문법/표현 첨삭'}
            </button>
          </div>
        </section>
=======
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
>>>>>>> 4c595276dbabe182f82a716684de89f60fec15ee

  return <Routes><Route path="/" element={<LandingPage />} /><Route path="/*" element={<AppLayout user={user} setUser={setUser} data={data} actions={actions} error={error} clearError={() => setError('')} />} /></Routes>;
}

export default function App() {
  return <BrowserRouter basename={import.meta.env.BASE_URL}><ParagraphyApp /></BrowserRouter>;
}
