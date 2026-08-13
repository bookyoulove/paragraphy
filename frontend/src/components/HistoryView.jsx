import { useEffect, useState } from 'react'
import { api } from '../api'
import { formatDateTime } from '../utils'

function ComparisonTable({ rounds }) {
  const roundsWithScores = rounds.filter((r) => r.criteria_scores)
  if (roundsWithScores.length === 0) return <p className="muted">아직 채점 완료된 회차가 없습니다.</p>

  // 회차마다 채점 기준이 동일하다고 가정(같은 세션 = 같은 문제/루브릭) — 1차 기준으로 행을 만든다
  const criteria = roundsWithScores[0].criteria_scores.map((c) => c.criterion)

  return (
    <div className="comparison-table-wrap">
      <table className="comparison-table">
        <thead>
          <tr>
            <th>채점 기준</th>
            {roundsWithScores.map((r) => (
              <th key={r.round}>{r.round}차</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {criteria.map((criterion) => (
            <tr key={criterion}>
              <td>{criterion}</td>
              {roundsWithScores.map((r) => {
                const found = r.criteria_scores.find((c) => c.criterion === criterion)
                return <td key={r.round}>{found ? `${found.score}/${found.max_score}` : '-'}</td>
              })}
            </tr>
          ))}
          <tr className="comparison-total-row">
            <td>총점</td>
            {roundsWithScores.map((r) => (
              <td key={r.round}>{r.total_score}</td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}

function SessionDetail({ sessionId, onBack }) {
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState('')
  const [openRound, setOpenRound] = useState(null)

  useEffect(() => {
    api
      .getSession(sessionId)
      .then(setDetail)
      .catch((e) => setError(e.message))
  }, [sessionId])

  if (error) return <div className="banner banner-error">{error}</div>
  if (!detail) return <p className="muted">불러오는 중…</p>

  return (
    <div>
      <button type="button" onClick={onBack}>
        ← 세션 목록으로
      </button>
      <h3>{detail.problem_title}</h3>
      <p className="muted">
        {detail.university || '사용자 입력'} {detail.year || ''} · 총 {detail.rounds.length}차 제출
      </p>

      <h4>초안 비교표</h4>
      <ComparisonTable rounds={detail.rounds} />

      <h4>회차별 답안</h4>
      {detail.rounds.map((r) => (
        <div className="round-item" key={r.round}>
          <button type="button" className="round-toggle" onClick={() => setOpenRound(openRound === r.round ? null : r.round)}>
            {r.round}차 · {formatDateTime(r.submitted_at)} · {r.total_score != null ? `${r.total_score}점` : '채점 실패'}
          </button>
          {openRound === r.round && (
            <div className="round-body">
              <p className="answer-text">{r.user_answer}</p>
              {r.overall_comment && <p className="overall-comment">{r.overall_comment}</p>}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default function HistoryView({ userIdentifier, onClose }) {
  const [sessions, setSessions] = useState([])
  const [error, setError] = useState('')
  const [selectedSessionId, setSelectedSessionId] = useState(null)

  useEffect(() => {
    api
      .listSessions(userIdentifier)
      .then(setSessions)
      .catch((e) => setError(e.message))
  }, [userIdentifier])

  return (
    <div className="history-overlay">
      <div className="history-panel">
        <div className="history-header">
          <h2>지난 세션 ({userIdentifier})</h2>
          <button type="button" onClick={onClose}>
            닫기
          </button>
        </div>
        {error && <div className="banner banner-error">{error}</div>}

        {selectedSessionId ? (
          <SessionDetail sessionId={selectedSessionId} onBack={() => setSelectedSessionId(null)} />
        ) : (
          <>
            {sessions.length === 0 && <p className="muted">아직 채점 이력이 없습니다.</p>}
            <ul className="session-list">
              {sessions.map((s) => (
                <li key={s.session_id} className="session-list-item" onClick={() => setSelectedSessionId(s.session_id)}>
                  <div>
                    <strong>{s.problem_title}</strong>
                    <p className="muted">
                      {s.university || '사용자 입력'} {s.year || ''} · {formatDateTime(s.created_at)}
                    </p>
                  </div>
                  <div className="session-list-meta">
                    <span>{s.round_count}회 제출</span>
                    {s.latest_total_score != null && <span className="session-score">{s.latest_total_score}점</span>}
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  )
}
