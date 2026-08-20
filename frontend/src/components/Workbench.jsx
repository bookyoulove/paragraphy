import { useEffect, useState } from 'react';
import ResultPanel from './ResultPanel';
import RubricModal from './RubricModal';

export default function Workbench({ problem, session, onSave, onGrade, readOnly = false }) {
  const [answer, setAnswer] = useState(session?.answer || '');
  const [showRubric, setShowRubric] = useState(false);
  const [saved, setSaved] = useState('');
  const [grading, setGrading] = useState(false);
  const [mode, setMode] = useState(readOnly ? 'view' : 'edit');
  const latestResult = session?.results.at(-1);
  const result = mode === 'new' ? null : latestResult;
  const editable = mode !== 'view';
  useEffect(() => {
    setAnswer(session?.answer ?? '');
    setSaved('');
    setMode(readOnly ? 'view' : 'edit');
  }, [session?.id, readOnly]);
  if (!problem)
    return (
      <div className="empty-state">
        <div className="label-title">먼저 문제를 선택해주세요</div>
        <div className="label-sub">
          왼쪽 메뉴의 문제 선택 또는 문제 직접 입력에서 시작할 수 있습니다.
        </div>
      </div>
    );
  const save = async () => {
    try {
      await onSave(answer, { createNew: mode === 'new' });
      setMode('edit');
      setSaved('답안이 저장되었습니다.');
      setTimeout(() => setSaved(''), 2200);
    } catch (err) {
      setSaved(err.message || '답안 저장에 실패했습니다.');
    }
  };
  const grade = async () => {
    setGrading(true);
    try {
      const savedSession = await onSave(answer, { createNew: mode === 'new' });
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
      <div className="answer-header">
        <div className="answer-title">{editable ? '답안 작성' : '답안 보기'}</div>
        <div className="word-counter">{answer.trim().length}자</div>
      </div>
      <div className="highlight-wrap">
        <textarea
          className="answer-input"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="여기에 답안을 작성하세요."
          readOnly={!editable}
          spellCheck="false"
        />
      </div>
      {editable ? (
        <div className="answer-actions">
          <span className="save-status">{saved}</span>
          <button className="primary-btn" onClick={save}>
            답안 저장
          </button>
          <button className="primary-btn" disabled={grading || !answer.trim()} onClick={grade}>
            {grading ? '채점 중...' : '채점 요청'}
          </button>
        </div>
      ) : (
        <div className="answer-actions">
          <span className="save-status" />
          <button
            className="primary-btn"
            onClick={() => {
              setAnswer('');
              setSaved('');
              setMode('new');
            }}
          >
            새로 풀기
          </button>
          <button className="primary-btn" onClick={() => setMode('edit')}>
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
  return (
    <>
      <div className="work-columns">
        <section className="column-slot">{result ? editor : detail}</section>
        <section className="column-slot">
          {result ? <ResultPanel result={result} results={session.results} /> : editor}
        </section>
      </div>
      {showRubric && (
        <RubricModal rubric={problem.rubric} onClose={() => setShowRubric(false)} readOnly />
      )}
    </>
  );
}
