import { useEffect, useState } from 'react';
import ResultPanel from './ResultPanel';

export default function Workbench({ problem, session, onSave, onGrade }) {
  const [answer, setAnswer] = useState(session?.answer || '');
  const [showRubric, setShowRubric] = useState(false);
  const [saved, setSaved] = useState('');
  const [grading, setGrading] = useState(false);
  const result = session?.results.at(-1);
  useEffect(() => {
    setAnswer(session?.answer ?? '');
    setSaved('');
  }, [session?.id]);
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
    await onSave(answer);
    setSaved('답안이 저장되었습니다.');
    setTimeout(() => setSaved(''), 2200);
  };
  const grade = async () => {
    setGrading(true);
    try {
      const savedSession = await onSave(answer);
      await onGrade(savedSession);
    } catch (err) {
      setSaved(err.message || '채점 요청에 실패했습니다.');
    } finally {
      setGrading(false);
    }
  };
  const editor = (
    <section className="answer-box">
      <div className="answer-header">
        <div className="answer-title">답안 작성</div>
        <div className="word-counter">{answer.trim().length}자</div>
      </div>
      <div className="highlight-wrap">
        <textarea
          className="answer-input"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="여기에 답안을 작성하세요."
          spellCheck="false"
        />
      </div>
      <div className="answer-actions">
        <span className="save-status">{saved}</span>
        <button className="primary-btn" onClick={save}>
          답안 저장
        </button>
        <button className="primary-btn" disabled={grading || !answer.trim()} onClick={grade}>
          {grading ? '채점 중...' : '채점 요청'}
        </button>
      </div>
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
        <div className="rubric-modal">
          <div className="rubric-modal-backdrop" onClick={() => setShowRubric(false)} />
          <div className="rubric-modal-card">
            <div className="rubric-modal-header">
              <div className="label-title">채점 기준</div>
              <button className="ghost-btn" onClick={() => setShowRubric(false)}>
                닫기 ✕
              </button>
            </div>
            <div className="rubric-modal-body">{problem.rubric}</div>
          </div>
        </div>
      )}
    </>
  );
}
