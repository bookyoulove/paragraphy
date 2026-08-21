import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';

const waitingMessage = {
  role: 'assistant',
  text: '채점이 완료되면 결과를 바탕으로 더 구체적인 도움을 드릴 수 있어요.',
};

const gradedGreeting = {
  role: 'assistant',
  text: '채점이 완료되었습니다! 궁금한 점을 Tutor에게 물어보세요.',
};

export default function TutorChatModal({ session, result: resultOverride }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([waitingMessage]);
  const [question, setQuestion] = useState('');
  // idle | connecting | open | closed | error
  const [status, setStatus] = useState('idle');
  const [waiting, setWaiting] = useState(false);
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const result = resultOverride ?? session?.results.at(-1);

  useEffect(() => {
    setMessages([result ? gradedGreeting : waitingMessage]);
  }, [session?.id, result?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: 'end' });
  }, [messages]);

  // 모달이 열려 있고 채점 결과가 있을 때만 연결한다.
  useEffect(() => {
    if (!isOpen || !result?.id) {
      setStatus('idle');
      return;
    }

    // React StrictMode(개발 모드)는 effect를 mount→cleanup→mount로 두 번 실행한다.
    // 첫 번째 소켓이 연결 완료 전에 닫히면서 그 이후 이벤트(onopen 등)가 뒤늦게
    // 도착해 상태를 덮어쓰는 레이스가 생길 수 있어, "이 effect 인스턴스가 아직
    // 유효한가"를 나타내는 로컬 플래그로 막는다 — 클로저로 캡처된 `active`가
    // cleanup 시 false가 되면, 그 소켓의 이후 이벤트는 전부 무시된다.
    let active = true;
    setStatus('connecting');
    setWaiting(false);
    const ws = new WebSocket(api.chatSocketUrl(result.id));
    wsRef.current = ws;

    ws.onopen = () => active && setStatus('open');
    ws.onclose = () => active && setStatus('closed');
    ws.onerror = () => active && setStatus('error');
    ws.onmessage = (event) => {
      if (!active) return;
      const data = JSON.parse(event.data);

      if (data.type === 'ready') {
        const history = (data.history || []).map((m, index) => ({
          id: `history-${index}`,
          role: m.role,
          text: m.content,
        }));
        setMessages(history.length ? history : [gradedGreeting]);
        return;
      }

      if (data.type === 'chunk') {
        // 마지막 메시지가 "생성 중인" assistant 말풍선이면 텍스트를 이어붙이고,
        // 아니면(이번 턴의 첫 조각) 새 말풍선을 만든다 — 타이핑 효과.
        setWaiting(false);
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === 'assistant' && last.streaming) {
            return [...prev.slice(0, -1), { ...last, text: last.text + data.content }];
          }
          return [...prev, { role: 'assistant', text: data.content, streaming: true }];
        });
        return;
      }

      if (data.type === 'done') {
        setWaiting(false);
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === 'assistant' && last.streaming) {
            return [...prev.slice(0, -1), { ...last, streaming: false }];
          }
          return prev;
        });
        return;
      }

      if (data.type === 'blocked') {
        setWaiting(false);
        setMessages((prev) => [
          ...prev,
          { role: 'blocked', text: data.reason || '이 질문은 정책상 답변할 수 없어요.' },
        ]);
        return;
      }

      if (data.type === 'error') {
        setWaiting(false);
        setMessages((prev) => [
          ...prev,
          { role: 'system', text: data.detail || 'Tutor 응답 중 오류가 발생했어요.' },
        ]);
      }
    };

    return () => {
      active = false;
      ws.close();
    };
  }, [isOpen, result?.id]);

  const send = () => {
    const text = question.trim();
    if (!text || !result || status !== 'open' || waiting) return;
    if (wsRef.current?.readyState !== WebSocket.OPEN) return; // 방어적 가드 (레이스로 남은 소켓 참조 방지)
    setQuestion('');
    setMessages((prev) => [...prev, { role: 'user', text }]);
    wsRef.current.send(text);
    setWaiting(true);
  };

  const boxClass = (role) => {
    if (role === 'assistant') return 'chat-assistant';
    if (role === 'blocked') return 'chat-blocked';
    if (role === 'system') return 'chat-system';
    return 'chat-user';
  };
  const badgeClass = (role) => {
    if (role === 'assistant') return 'assistant';
    if (role === 'blocked') return 'blocked';
    if (role === 'system') return 'system';
    return '';
  };
  const badgeLabel = (role) => {
    if (role === 'assistant') return 'AI';
    if (role === 'blocked') return '⚠';
    if (role === 'system') return '!';
    return '나';
  };

  const inputDisabled = !result || status !== 'open' || waiting;
  const placeholder = !result
    ? '답안을 채점한 뒤 질문할 수 있어요'
    : status === 'connecting'
      ? '연결하는 중...'
      : waiting
        ? 'Tutor가 답변을 작성 중입니다…'
        : 'Tutor에게 질문하기';

  return (
    <>
      <button
        type="button"
        className="tutor-chat-fab"
        onClick={() => setIsOpen(true)}
        aria-label="Tutor Chat 열기"
        title="Tutor Chat"
      >
        <span aria-hidden="true">✦</span>
      </button>
      {isOpen && (
        <div className="tutor-chat-modal" role="dialog" aria-modal="true" aria-label="Tutor Chat">
          <button
            type="button"
            className="tutor-chat-backdrop"
            aria-label="Tutor Chat 닫기"
            onClick={() => setIsOpen(false)}
          />
          <section className="tutor-chat-card">
            <header className="tutor-chat-header">
              <div>
                <strong>Tutor Chat</strong>
                <span>
                  {result
                    ? '채점 결과를 바탕으로 답변합니다.'
                    : '채점 후 상세 피드백을 받을 수 있습니다.'}
                </span>
              </div>
              <button className="ghost-btn" onClick={() => setIsOpen(false)}>
                닫기 ✕
              </button>
            </header>
            <div className="chat-messages">
              {status === 'connecting' && <div className="chat-loading">연결하는 중...</div>}
              {status === 'error' && (
                <div className="chat-loading chat-loading-error">
                  연결에 실패했어요. 잠시 후 다시 시도해주세요.
                </div>
              )}
              {messages.map((message, index) => (
                <div
                  className={`chat-box ${boxClass(message.role)}`}
                  key={message.id ?? `${message.role}-${index}`}
                >
                  <div className={`chat-badge ${badgeClass(message.role)}`}>
                    {badgeLabel(message.role)}
                  </div>
                  <div className="chat-msg">
                    {message.text}
                    {message.streaming && <span className="chat-caret" />}
                  </div>
                </div>
              ))}
              {waiting && (
                <div className="chat-box chat-assistant">
                  <div className="chat-badge assistant">AI</div>
                  <div className="chat-msg chat-typing-msg">
                    Tutor가 답변을 생각하고 있어요
                    <span className="typing-dots">
                      <span>.</span>
                      <span>.</span>
                      <span>.</span>
                    </span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            <div className="chat-input-wrap">
              <input
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => event.key === 'Enter' && send()}
                placeholder={placeholder}
                disabled={inputDisabled}
              />
              <button className="primary-btn small-btn" disabled={inputDisabled} onClick={send}>
                전송
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
