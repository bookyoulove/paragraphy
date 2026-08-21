import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AnnotatedAnswer from './AnnotatedAnswer';
import ResultPanel from './ResultPanel';
import RubricModal from './RubricModal';

const initialMode = (session, readOnly, startNew) => {
  if (readOnly) return 'view';
  if (startNew) return 'new';
  return session?.answerSubmitted ? 'view' : 'edit';
};

const formatElapsedTime = (seconds) => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`;
};

export default function Workbench({
  problem,
  session,
  onSave,
  onGrade,
  onNewAnswerStateChange,
  answerOverride = null,
  resultOverride,
  onNewAnswer,
  onEditAnswer,
  readOnly = false,
  startNew = false,
}) {
  const navigate = useNavigate();
  const answerValue = answerOverride?.userAnswer ?? session?.answer ?? '';
  const answerName = answerOverride?.name ?? session?.answerName ?? '';
  const [answer, setAnswer] = useState(startNew ? '' : answerValue);
  const [name, setName] = useState(startNew ? '' : answerName);
  const [showRubric, setShowRubric] = useState(false);
  const [saved, setSaved] = useState('');
  const [grading, setGrading] = useState(false);
  const [gradingElapsedSeconds, setGradingElapsedSeconds] = useState(0);
  const [mode, setMode] = useState(() => initialMode(session, readOnly, startNew));
  const [selectedCorrectionIndex, setSelectedCorrectionIndex] = useState(null);
  const [proofFocusId, setProofFocusId] = useState(0);
  const startedNewRoundRef = useRef(false);
  const latestResult = resultOverride === undefined ? session?.results.at(-1) : resultOverride;
  const result = mode === 'new' ? null : latestResult;
  const editable = mode !== 'view';
  const pendingNewRound = mode === 'new';
  useEffect(() => {
    if (startNew && !startedNewRoundRef.current) {
      startedNewRoundRef.current = true;
      setAnswer('');
      setName('');
      setSaved('');
      setMode('new');
      setSelectedCorrectionIndex(null);
      return;
    }
    if (!startNew) startedNewRoundRef.current = false;
    setAnswer(startNew ? '' : answerValue);
    setName(startNew ? '' : answerName);
    setSaved('');
    setMode(initialMode(session, readOnly, startNew));
    setSelectedCorrectionIndex(null);
  }, [session?.id, answerOverride?.id, readOnly, startNew]);
  useEffect(() => {
    onNewAnswerStateChange?.(mode === 'new');
  }, [mode, onNewAnswerStateChange]);
  useEffect(() => {
    if (!grading) return undefined;

    const startedAt = Date.now();
    setGradingElapsedSeconds(0);
    const timer = window.setInterval(() => {
      setGradingElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);

    return () => window.clearInterval(timer);
  }, [grading]);
  if (!problem)
    return (
      <div className="empty-state">
        <div className="label-title">먼저 문제를 선택해주세요</div>
        <div className="label-sub">
          왼쪽 메뉴의 문제 선택 또는 문제 직접 입력에서 시작할 수 있습니다.
        </div>
      </div>
    );
  const startNewAnswer = () => {
    if (onNewAnswer) {
      onNewAnswer();
      return;
    }
    setAnswer('');
    setName('');
    setSaved('');
    setMode('new');
  };
  const editAnswer = () => {
    if (onEditAnswer) {
      onEditAnswer();
      return;
    }
    setMode('edit');
  };
  const save = async () => {
    try {
      await onSave(answer, { createNew: pendingNewRound, name });
      setMode('edit');
      setSaved('임시 저장되었습니다.');
      setTimeout(() => setSaved(''), 2200);
    } catch (err) {
      setSaved(err.message || '임시 저장에 실패했습니다.');
    }
  };
  const grade = async () => {
    setGrading(true);
    try {
      const savedSession = await onSave(answer, { createNew: pendingNewRound, name });
      await onGrade(savedSession);
      setMode('view');
    } catch (err) {
      setSaved(err.message || '채점 요청에 실패했습니다.');
    } finally {
      setGrading(false);
    }
  };
  const editor = (
    <section className="answer-box">
      {pendingNewRound && session?.answers?.length > 0 && (
        <div className="new-round-notice">
          <span>
            이 문제에 이전 답안 {session.answers.length}개가 있습니다. 새 답안은 새 회차로
            저장됩니다.
          </span>
          <button
            type="button"
            className="ghost-btn"
            onClick={() => navigate(`/history/${session.id}`)}
          >
            이전 답안 보기
          </button>
        </div>
      )}
      <div className="answer-header">
        <div className="answer-title">{editable ? '답안 작성' : '답안 보기'}</div>
        {editable && (
          <input
            className="answer-name-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={grading}
            maxLength={50}
            placeholder={pendingNewRound ? '답안 이름 (비워두면 자동으로 N회차)' : '답안 이름'}
            aria-label="답안 이름"
          />
        )}
        <div className="word-counter">{answer.trim().length}자</div>
      </div>
      <div className="highlight-wrap">
        {!editable && result ? (
          <AnnotatedAnswer
            text={answer}
            corrections={result.errors}
            selectedIndex={selectedCorrectionIndex}
            onSelect={(index) => {
              setSelectedCorrectionIndex(index);
              if (index !== null) setProofFocusId((value) => value + 1);
            }}
          />
        ) : (
          <textarea
            className="answer-input"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="여기에 답안을 작성하세요."
            spellCheck="false"
            disabled={grading}
          />
        )}
      </div>
      {editable ? (
        <div className="answer-actions">
          <span className="save-status">{saved}</span>
          <button className="primary-btn" disabled={grading} onClick={save}>
            임시 저장
          </button>
          <button className="primary-btn" disabled={grading || !answer.trim()} onClick={grade}>
            {grading ? '채점 중...' : '채점 요청'}
          </button>
        </div>
      ) : (
        <div className="answer-actions">
          <span className="save-status" />
          <button className="primary-btn" onClick={startNewAnswer}>
            새로 풀기
          </button>
          <button className="primary-btn" onClick={editAnswer}>
            수정하기
          </button>
        </div>
      )}
    </section>
  );
  const detail = (
    <section className="problem-box">
      <div className="problem-header">
        <div className="problem-title">{problem.title}</div>
        <div className="problem-header-actions">
          <button className="ghost-btn" onClick={() => setShowRubric(true)}>
            채점 기준 보기
          </button>
        </div>
      </div>
      <div id="problemBody">
        <div className="problem-text">{problem.content}</div>
      </div>
    </section>
  );
  const gradingPanel = (
    <aside className="right-panel" aria-live="polite" aria-busy="true">
      <div className="tabs">
        <div className="tab active">채점 결과</div>
      </div>
      <div className="panel-loading">
        <div className="grade-loading-spinner" aria-hidden="true" />
        <div className="grade-loading-text">답안을 채점하고 있어요</div>
        <div className="grade-loading-sub">경과 시간 {formatElapsedTime(gradingElapsedSeconds)}</div>
        <div className="grade-loading-sub">약 1분 정도 소요됩니다. 잠시만 기다려주세요.</div>
      </div>
    </aside>
  );
  return (
    <>
      <div className="work-columns">
        <section className="column-slot">{result || readOnly || grading ? editor : detail}</section>
        <section className="column-slot">
          {grading ? (
            gradingPanel
          ) : result || readOnly ? (
            <ResultPanel
              sessionId={session.id}
              result={result}
              results={session.results}
              selectedCorrectionIndex={selectedCorrectionIndex}
              proofFocusId={proofFocusId}
              onSelectCorrection={setSelectedCorrectionIndex}
            />
          ) : (
            editor
          )}
        </section>
      </div>
      {showRubric && (
        <RubricModal rubric={problem.rubric} onClose={() => setShowRubric(false)} readOnly />
      )}
    </>
  );
}
