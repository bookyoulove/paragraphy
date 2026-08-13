import { useEffect, useRef, useState } from 'react'
import { WS_BASE } from '../api'

export default function ChatPanel({ resultId, userIdentifier }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [status, setStatus] = useState('idle') // idle | connecting | open | closed | error
  const wsRef = useRef(null)

  useEffect(() => {
    if (!resultId) {
      setStatus('idle')
      setMessages([])
      return
    }

    setStatus('connecting')
    const url = `${WS_BASE}/api/chat?result_id=${encodeURIComponent(resultId)}&user_identifier=${encodeURIComponent(userIdentifier)}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setStatus('open')
    ws.onclose = () => setStatus('closed')
    ws.onerror = () => setStatus('error')
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'ready') {
        setMessages(data.history || [])
      } else if (data.type === 'message') {
        setMessages((prev) => [...prev, { role: data.role, content: data.content }])
      } else if (data.type === 'error') {
        setMessages((prev) => [...prev, { role: 'system', content: `⚠ ${data.detail}` }])
      }
    }

    return () => ws.close()
  }, [resultId, userIdentifier])

  const send = () => {
    if (!input.trim() || status !== 'open') return
    setMessages((prev) => [...prev, { role: 'user', content: input }])
    wsRef.current.send(input)
    setInput('')
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
            <strong>{m.role === 'user' ? '나' : m.role === 'assistant' ? 'Tutor' : '시스템'}</strong>
            <p>{m.content}</p>
          </div>
        ))}
      </div>
      <div className="chat-input-row">
        <input
          value={input}
          disabled={status !== 'open'}
          placeholder="예: 왜 이 점수가 나왔어? 어떻게 고치면 좋을까?"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
        />
        <button type="button" onClick={send} disabled={status !== 'open'}>
          전송
        </button>
      </div>
    </div>
  )
}
