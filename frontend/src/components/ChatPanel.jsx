import { useEffect, useRef, useState } from 'react'
import { WS_BASE } from '../api'

export default function ChatPanel({ resultId, userIdentifier }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [status, setStatus] = useState('idle') // idle | connecting | open | closed | error
  const [isStreaming, setIsStreaming] = useState(false)
  const wsRef = useRef(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: 'end' })
  }, [messages])

  useEffect(() => {
    if (!resultId) {
      setStatus('idle')
      setMessages([])
      return
    }

    // React StrictMode(개발 모드)는 effect를 mount→cleanup→mount로 두 번 실행한다.
    // 첫 번째 소켓이 연결 완료 전에 닫히면서 그 이후 이벤트(onopen 등)가 뒤늦게
    // 도착해 상태를 덮어쓰는 레이스가 생길 수 있어, "이 effect 인스턴스가 아직
    // 유효한가"를 나타내는 로컬 플래그로 막는다 — 클로저로 캡처된 `active`가
    // cleanup 시 false가 되면, 그 소켓의 이후 이벤트는 전부 무시된다.
    let active = true
    setStatus('connecting')
    setIsStreaming(false)
    const url = `${WS_BASE}/api/chat?result_id=${encodeURIComponent(resultId)}&user_identifier=${encodeURIComponent(userIdentifier)}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => active && setStatus('open')
    ws.onclose = () => active && setStatus('closed')
    ws.onerror = () => active && setStatus('error')
    ws.onmessage = (event) => {
      if (!active) return
      const data = JSON.parse(event.data)

      if (data.type === 'ready') {
        setMessages((data.history || []).map((m) => ({ ...m, streaming: false })))
        return
      }

      if (data.type === 'chunk') {
        // 마지막 메시지가 "생성 중인" assistant 말풍선이면 텍스트를 이어붙이고,
        // 아니면(이번 턴의 첫 조각) 새 말풍선을 만든다 — 타이핑 효과.
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last && last.role === 'assistant' && last.streaming) {
            const updated = { ...last, content: last.content + data.content }
            return [...prev.slice(0, -1), updated]
          }
          return [...prev, { role: 'assistant', content: data.content, streaming: true }]
        })
        return
      }

      if (data.type === 'done') {
        setIsStreaming(false)
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last && last.role === 'assistant' && last.streaming) {
            return [...prev.slice(0, -1), { ...last, streaming: false }]
          }
          return prev
        })
        return
      }

      if (data.type === 'blocked') {
        setIsStreaming(false)
        setMessages((prev) => [...prev, { role: 'blocked', content: data.reason }])
        return
      }

      if (data.type === 'error') {
        setIsStreaming(false)
        setMessages((prev) => [...prev, { role: 'system', content: `⚠ ${data.detail}` }])
      }
    }

    return () => {
      active = false
      ws.close()
    }
  }, [resultId, userIdentifier])

  const send = () => {
    if (!input.trim() || status !== 'open' || isStreaming) return
    if (wsRef.current?.readyState !== WebSocket.OPEN) return // 방어적 가드 (레이스로 남은 소켓 참조 방지)
    setMessages((prev) => [...prev, { role: 'user', content: input }])
    wsRef.current.send(input)
    setInput('')
    setIsStreaming(true)
  }

  const roleLabel = (role) => {
    if (role === 'user') return '나'
    if (role === 'assistant') return 'Tutor'
    if (role === 'blocked') return '⚠ 입력 차단'
    return '시스템'
  }

  return (
    <div className="chat-panel">
      <h3>
        Tutor Chat <span className={`chat-status chat-status-${status}`}>({status})</span>
      </h3>
      {!resultId && <p className="muted">먼저 채점을 완료하면 채팅을 시작할 수 있습니다.</p>}
      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={`chat-message chat-message-${m.role}`}>
            <strong>{roleLabel(m.role)}</strong>
            <p>
              {m.content}
              {m.streaming && <span className="chat-caret" />}
            </p>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="chat-input-row">
        <input
          value={input}
          disabled={status !== 'open' || isStreaming}
          placeholder={isStreaming ? 'Tutor가 답변을 작성 중입니다…' : '예: 왜 이 점수가 나왔어? 어떻게 고치면 좋을까?'}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
        />
        <button type="button" onClick={send} disabled={status !== 'open' || isStreaming}>
          전송
        </button>
      </div>
    </div>
  )
}