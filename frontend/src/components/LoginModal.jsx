import { useState } from 'react';
import Brand from './Brand';

export default function LoginModal({ onLogin }) {
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const submit = () => {
    if (!name.trim()) return setError('식별자를 입력해주세요.');
    onLogin({ id: 1, identifier: name.trim() });
  };
  return (
    <div className="login-overlay">
      <div className="login-card">
        <Brand />
        <div className="login-sub">
          식별자(이름/별명)를 입력하세요. 샘플 화면에서는 브라우저 안에서만 보관됩니다.
        </div>
        <input
          className="select-input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          placeholder="예: 유진"
          autoFocus
        />
        <button className="primary-btn full-width" onClick={submit}>
          시작하기
        </button>
        <div className="login-error">{error}</div>
      </div>
    </div>
  );
}
