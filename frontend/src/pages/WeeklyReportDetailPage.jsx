import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client';

const labels = {
  claim: '주장',
  evidence_relevance: '이유·근거의 적절성',
  evidence_sufficiency: '이유·근거의 충분성',
  counterargument: '다른 입장에 대한 고려',
  passage_summary: '지문 요약',
};

export default function WeeklyReportDetailPage({ user, onRefreshProblems }) {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [recipientEmail, setRecipientEmail] = useState('');
  const [mailStatus, setMailStatus] = useState('');
  const [sendingEmail, setSendingEmail] = useState(false);
  const [generatingProblem, setGeneratingProblem] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.getSkillReport(reportId).then(setReport).catch((err) => setError(err.message));
  }, [user, reportId]);

  if (error) return <div className="panel-empty">{error}</div>;
  if (!report) return <div className="panel-empty">주간 리포트를 불러오는 중입니다.</div>;

  const start = new Date(report.period_start);
  const end = new Date(report.period_end);
  const sendEmail = async (event) => {
    event.preventDefault();
    setMailStatus('');
    setSendingEmail(true);
    try {
      await api.sendSkillReportEmail(report.id, recipientEmail);
      setMailStatus('메일 발송을 요청했습니다. 잠시 후 받은메일함을 확인해 주세요.');
    } catch (err) {
      setMailStatus(err.message || '메일 발송 요청에 실패했습니다.');
    } finally {
      setSendingEmail(false);
    }
  };
  const generateProblem = async () => {
    setGeneratingProblem(true);
    try {
      await api.generateProblemFromReport(report.id);
      await onRefreshProblems();
      navigate('/problems');
    } catch (err) {
      setError(err.message || '맞춤 문제 생성에 실패했습니다.');
    } finally {
      setGeneratingProblem(false);
    }
  };
  return (
    <section className="weekly-report-page weekly-report-detail">
      <button type="button" className="ghost-btn" onClick={() => navigate('/weekly-reports')}>← 주간 분석 목록</button>
      <header className="weekly-report-header">
        <div>
          <p className="page-eyebrow">{start.getFullYear()}년 {start.getMonth() + 1}월 {Math.ceil(start.getDate() / 7)}주차</p>
          <h1>주간 학습 리포트</h1>
          <p>{start.toLocaleDateString('ko-KR')} ~ {end.toLocaleDateString('ko-KR')} · {report.review_count}문제 풀이</p>
        </div>
        <form className="weekly-email-form" onSubmit={sendEmail}>
          <label htmlFor="weekly-report-email">리포트 메일 받기</label>
          <div>
            <input
              id="weekly-report-email"
              type="email"
              value={recipientEmail}
              onChange={(event) => setRecipientEmail(event.target.value)}
              placeholder="you@example.com"
              required
            />
            <button className="primary-btn" type="submit" disabled={sendingEmail}>
              {sendingEmail ? '전송 요청 중...' : '메일로 보내기'}
            </button>
          </div>
          {mailStatus && <p role="status">{mailStatus}</p>}
        </form>
      </header>
      <section className="weekly-problem-cta">
        <div><strong>취약 영역 보완 문제</strong><p>이 리포트의 가장 낮은 역량을 집중적으로 연습할 새 문제를 만듭니다.</p></div>
        <button className="primary-btn" type="button" onClick={generateProblem} disabled={generatingProblem}>
          {generatingProblem ? '문제 생성 중...' : '맞춤 문제 만들기'}
        </button>
      </section>
      <div className="skill-score-grid">
        {report.skill_scores.map((score) => (
          <article className="skill-score-card" key={score.key}>
            <div className="skill-score-card-head"><span>{labels[score.key] ?? score.key}</span><strong>{score.score}<small>/5</small></strong></div>
            <p>{score.rationale}</p>
            <div><b>개선 방향</b>{score.improvement}</div>
          </article>
        ))}
      </div>
      <section className="weekly-summary-card">
        <h2>종합 코멘트</h2><p>{report.overall_skill_comment}</p>
        <h2>다음 학습 목표</h2><p>{report.next_learning_goal}</p>
        <h2>이번 주 실천하기</h2>
        <ul>{report.recommended_actions.map((action) => <li key={action}>{action}</li>)}</ul>
      </section>
    </section>
  );
}
