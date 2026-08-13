import { useEffect, useState } from 'react'
import { api } from './api'
import RubricEditor from './components/RubricEditor.jsx'
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
  const [problemCollapsed, setProblemCollapsed] = useState(false)

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

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-left">
          <span className="logo-badge">P</span>
          <div>
            <h1>Paragraphy</h1>
            <p className="muted">대입 논술 채점 · 첨삭</p>
          </div>
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

      <main className="app-grid-2col">
        <section className="panel editor-panel">
          <div className="section-head">
            <h2>논술 문항</h2>
            <button type="button" className="link-button" onClick={() => setProblemCollapsed((v) => !v)}>
              {problemCollapsed ? '펼치기' : '접기'}
            </button>
          </div>

          {!problemCollapsed && (
            <>
              <div className="mode-toggle">
                <button type="button" className={mode === 'bank' ? 'active' : ''} onClick={() => setMode('bank')}>
                  문제은행에서 선택
                </button>
                <button type="button" className={mode === 'custom' ? 'active' : ''} onClick={() => setMode('custom')}>
                  직접 입력
                </button>
              </div>

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
                      <RubricEditor items={selectedProblem.rubrics} editable={false} onChange={() => {}} />
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
                  <RubricEditor
                    items={customRubric}
                    editable
                    onChange={setCustomRubric}
                    onSuggest={handleSuggestRubric}
                    suggesting={suggesting}
                  />
                </>
              )}
            </>
          )}

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

        <section className="panel result-panel-outer">
          <div className="tab-bar">
            {TABS.map((t) => (
              <button key={t.key} type="button" className={activeTab === t.key ? 'active' : ''} onClick={() => setActiveTab(t.key)}>
                {t.label}
              </button>
            ))}
          </div>
          <div className="tab-content">
            {activeTab === 'grading' && <GradingTab result={gradingResult} />}
            {activeTab === 'feedback' && <FeedbackTab result={feedbackResult} />}
            {activeTab === 'chat' && <ChatPanel resultId={gradingResult?.result_id} userIdentifier={userIdentifier} />}
          </div>
        </section>
      </main>

      {showHistory && <HistoryView userIdentifier={userIdentifier} onClose={() => setShowHistory(false)} />}
    </div>
  )
}
