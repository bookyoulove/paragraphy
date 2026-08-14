import { useEffect, useState } from 'react';

const waitingMessage = {
  role: 'assistant',
  text: '채점이 완료되면 결과를 바탕으로 더 구체적인 도움을 드릴 수 있어요.',
};

export default function TutorChatModal({ session, onChat }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([waitingMessage]);
  const [question, setQuestion] = useState('');
  const [waiting, setWaiting] = useState(false);
  const result = session?.results.at(-1);

  useEffect(() => {
    setMessages([
      result
        ? { role: 'assistant', text: '채점이 완료되었습니다! 궁금한 점을 Tutor에게 물어보세요.' }
        : waitingMessage,
    ]);
  }, [session?.id, result?.attempt]);

  const send = async () => {
    const text = question.trim();
    if (!text || !result) return;
    setQuestion('');
    setMessages((old) => [...old, { role: 'user', text }]);
    setWaiting(true);
    const reply = await onChat(text, result);
    setMessages((old) => [...old, { role: 'assistant', text: reply }]);
    setWaiting(false);
  };

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
              {messages.map((message, index) => (
                <div
                  className={`chat-box ${message.role === 'assistant' ? 'chat-assistant' : 'chat-user'}`}
                  key={`${message.role}-${index}`}
                >
                  <div className={`chat-badge ${message.role === 'assistant' ? 'assistant' : ''}`}>
                    {message.role === 'assistant' ? 'AI' : '나'}
                  </div>
                  <div className="chat-msg">{message.text}</div>
                </div>
              ))}
              {waiting && (
                <div className="chat-box chat-assistant">
                  <div className="chat-badge assistant">AI</div>
                  <div className="chat-msg">Tutor가 답변을 생각하고 있어요...</div>
                </div>
              )}
            </div>
            <div className="chat-input-wrap">
              <input
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => event.key === 'Enter' && send()}
                placeholder={result ? 'Tutor에게 질문하기' : '답안을 채점한 뒤 질문할 수 있어요'}
                disabled={!result || waiting}
              />
              <button
                className="primary-btn small-btn"
                disabled={!result || waiting}
                onClick={send}
              >
                전송
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
