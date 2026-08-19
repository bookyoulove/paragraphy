import { useState } from 'react';
import RubricItems from './RubricItems';

const createInitialForm = () => ({
  title: '',
  content: '',
  rubrics: [{ criteria: '', description: '' }],
});

export default function CustomProblemForm({ onGenerate, onCreate }) {
  const [form, setForm] = useState(createInitialForm);
  const [status, setStatus] = useState('');
  const patch = (key, value) => setForm((old) => ({ ...old, [key]: value }));
  const generate = async () => {
    if (!form.content.trim()) return setStatus('먼저 문제 본문을 입력하세요.');
    setStatus('샘플 AI가 채점 기준을 생성하는 중입니다...');
    try {
      patch('rubrics', await onGenerate(form));
      setStatus('생성된 샘플 채점 기준입니다. 수정 후 저장할 수 있습니다.');
    } catch (err) {
      setStatus(err.message || '채점 기준 생성에 실패했습니다.');
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
  return (
    <div className="picker-view">
      <div className="picker-view-header">
        <div>
          <div className="label-title">문제 직접 입력</div>
          <div className="label-sub">
            문제와 채점 기준을 직접 입력하거나 샘플 AI로 생성할 수 있습니다.
          </div>
        </div>
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
        <button type="button" className="ghost-btn" onClick={generate}>
          AI로 채점기준 생성
        </button>
      </div>
      <div className="rubric-editor">
        <RubricItems items={form.rubrics} onChange={(rubrics) => patch('rubrics', rubrics)} />
      </div>
      <div className="session-status">{status}</div>
      <button type="button" className="primary-btn full-width" onClick={create}>
        이 문제로 저장하고 선택
      </button>
    </div>
  );
}
