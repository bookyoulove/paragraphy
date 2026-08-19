import { useState } from 'react';
import Brand from './Brand';

export default function LoginModal({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const submit = async () => {
    if (!username.trim() || !password) return setError('사용자 이름과 비밀번호를 입력해주세요.');
    try {
      await onLogin({ username: username.trim(), password });
    } catch (err) {
      setError('로그인에 실패했습니다. 백엔드 연결을 확인하세요.');
    }
  };
  return (
    <div className="login-overlay">
      <div className="login-card">
        <Brand />
        <div className="login-sub">사용자 이름과 비밀번호를 입력해 로그인하세요.</div>
        <label className="field-label" htmlFor="loginUsername">
          사용자 이름
        </label>
        <input
          id="loginUsername"
          className="select-input"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          placeholder="예: yujin"
          autoFocus
        />
        <label className="field-label" htmlFor="loginPassword">
          비밀번호
        </label>
        <input
          id="loginPassword"
          className="select-input"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          placeholder="비밀번호 입력"
        />
        <button className="primary-btn full-width" onClick={submit}>
          시작하기
        </button>
        <div className="login-error">{error}</div>
      </div>
    </div>
  );
}
