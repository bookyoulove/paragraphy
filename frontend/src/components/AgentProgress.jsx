import { useEffect, useState } from 'react';
import './AgentProgress.css';

const EXPECTED_SECONDS = 30;

function formatElapsed(seconds) {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`;
}

export default function AgentProgress({ task }) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!task) return undefined;
    const updateElapsed = () => {
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - task.startedAt) / 1000)));
    };
    updateElapsed();
    const timer = window.setInterval(updateElapsed, 1000);
    return () => window.clearInterval(timer);
  }, [task]);

  if (!task) return null;

  const isSlow = elapsedSeconds >= EXPECTED_SECONDS;
  const progress = isSlow ? 100 : Math.max(4, (elapsedSeconds / EXPECTED_SECONDS) * 100);

  return (
    <div className={`agent-progress ${isSlow ? 'is-slow' : ''}`} role="status" aria-live="polite">
      <div className="agent-progress-content">
        <span className="agent-progress-spinner" aria-hidden="true" />
        <div className="agent-progress-copy">
          <strong>
            {isSlow ? `${task.label}이 생각보다 오래 걸리고 있어요` : `${task.label} 중...`}
          </strong>
          <span>예상 시간 약 30초 · 경과 {formatElapsed(elapsedSeconds)}</span>
        </div>
      </div>
      <div className="agent-progress-track" aria-hidden="true">
        <div className="agent-progress-bar" style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}
