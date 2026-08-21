import { useState } from 'react';
import MyProblemsModal from './MyProblemsModal';
import RubricItems from './RubricItems';

const createInitialForm = () => ({
  title: '',
  content: '',
  rubrics: [{ criteria: '', description: '' }],
});

export default function CustomProblemForm({
  myProblems,
  onGenerate,
  onCreate,
  onSelectExisting,
  onDeleteProblem,
  onRecommend,
}) {
  const [form, setForm] = useState(createInitialForm);
  const [status, setStatus] = useState('');
  const [showMyProblems, setShowMyProblems] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [searching, setSearching] = useState(false);
  const [generatingRubric, setGeneratingRubric] = useState(false);
  const [recommendResult, setRecommendResult] = useState(null);
  const [recommendError, setRecommendError] = useState('');
  const patch = (key, value) => setForm((old) => ({ ...old, [key]: value }));
  const generate = async () => {
    if (!form.content.trim()) return setStatus('먼저 문제 본문을 입력하세요.');
    setGeneratingRubric(true);
    setStatus('AI가 채점 기준을 생성하는 중입니다...');
    try {
      patch('rubrics', await onGenerate(form));
      setStatus('생성된 샘플 채점 기준입니다. 수정 후 저장할 수 있습니다.');
    } catch (err) {
      setStatus(err.message || '채점 기준 생성에 실패했습니다.');
    } finally {
      setGeneratingRubric(false);
    }
  };
  const create = async () => {
    if (!form.title.trim() || !form.content.trim())
      return setStatus('문제 제목과 본문을 입력하세요.');
    try {
      const created = await onCreate(form);
      if (created === false) return;
      setForm(createInitialForm());
      setStatus('');
    } catch (err) {
      setStatus(err.message || '문제 저장에 실패했습니다.');
    }
  };
  const search = async () => {
    if (!keyword.trim()) return setRecommendError('검색할 키워드를 입력하세요.');
    setSearching(true);
    setRecommendError('');
    setRecommendResult(null);
    try {
      setRecommendResult(await onRecommend(keyword.trim()));
    } catch (err) {
      setRecommendError(err.message || '추천 문제 검색에 실패했습니다.');
    } finally {
      setSearching(false);
    }
  };
  const applyRecommended = (title, content) => {
    setForm({ title, content, rubrics: [{ criteria: '', description: '' }] });
    setRecommendResult(null);
    setKeyword('');
    setStatus('추천 문제를 불러왔습니다. 채점 기준을 생성한 뒤 저장하세요.');
  };
  return (
    <div className="picker-view">
      <div className="picker-view-header">
        <div>
          <div className="label-title">문제 직접 입력</div>
          <div className="label-sub">
            문제와 채점 기준을 직접 입력하거나 샘플 AI로 생성할 수 있습니다.
          </div>
        </div>
        <button className="ghost-btn" onClick={() => setShowMyProblems(true)}>
          직접 입력한 문제 목록
        </button>
      </div>

      <div className="recommend-box">
        <label className="field-label">키워드별 추천 문제</label>
        <div className="recommend-input-row">
          <input
            className="select-input"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
            placeholder="예: 동물원, 인공지능, 탄소세..."
          />
          <button type="button" className="ghost-btn" disabled={searching} onClick={search}>
            {searching ? '검색 중...' : '검색'}
          </button>
        </div>
        {recommendError && <div className="recommend-error">{recommendError}</div>}
        {recommendResult && recommendResult.matches.length > 0 && (
          <div className="problem-list recommend-list">
            {recommendResult.matches.map((item) => (
              <button
                key={item.label}
                className="problem-card"
                onClick={() => applyRecommended(item.title, item.content)}
              >
                <span className="card-title">
                  [{item.label}] {item.title}
                </span>
                <span className="card-meta">{item.category} 분야</span>
              </button>
            ))}
          </div>
        )}
        {recommendResult && recommendResult.matches.length === 0 && recommendResult.generated && (
          <div className="problem-list recommend-list">
            <div className="recommend-generated-note">
              비슷한 문제를 찾지 못해 AI가 새 문제를 생성했습니다.
            </div>
            <button
              className="problem-card"
              onClick={() =>
                applyRecommended(recommendResult.generated.title, recommendResult.generated.content)
              }
            >
              <span className="card-title">[AI 생성] {recommendResult.generated.title}</span>
              <span className="card-meta">{recommendResult.generated.content}</span>
            </button>
          </div>
        )}
      </div>

      <label className="field-label">문제 제목</label>
      <input
        className="select-input"
        value={form.title}
        onChange={(e) => patch('title', e.target.value)}
        placeholder="예: SNS 알고리즘 규제 찬반"
      />
      <label className="field-label">문제 본문 / 제시문</label>
      <textarea
        className="custom-textarea"
        value={form.content}
        onChange={(e) => patch('content', e.target.value)}
        placeholder="문제(발문)와 제시문을 입력하세요."
      />
      <div className="rubric-row">
        <label className="field-label">채점 기준</label>
        <button type="button" className="ghost-btn" onClick={generate} disabled={generatingRubric}>
          {generatingRubric ? '생성 중...' : 'AI로 채점기준 생성'}
        </button>
      </div>
      <div className="rubric-editor">
        <RubricItems items={form.rubrics} onChange={(rubrics) => patch('rubrics', rubrics)} />
      </div>
      <div className="session-status">{status}</div>
      <button type="button" className="primary-btn full-width" onClick={create}>
        문제 저장
      </button>
      {showMyProblems && (
        <MyProblemsModal
          problems={myProblems}
          onClose={() => setShowMyProblems(false)}
          onSelect={(problem) => {
            setShowMyProblems(false);
            onSelectExisting(problem);
          }}
          onDelete={onDeleteProblem}
        />
      )}
    </div>
  );
}
