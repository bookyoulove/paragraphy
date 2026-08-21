import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

function formatPeriod(report) {
  const start = new Date(report.period_start);
  const end = new Date(report.period_end);
  return `${start.getMonth() + 1}.${start.getDate()} ~ ${end.getMonth() + 1}.${end.getDate()}`;
}

export default function WeeklyReportsPage({ user, onCreateReport }) {
  const navigate = useNavigate();
  const [reports, setReports] = useState(null);
  const [error, setError] = useState('');
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.getSkillReports().then(setReports).catch((err) => setError(err.message));
  }, [user]);

  const createReport = async () => {
    setError('');
    setGenerating(true);
    try {
      const report = await onCreateReport();
      navigate(`/weekly-reports/${report.id}`);
    } catch (err) {
      setError(err.message || '주간 리포트 생성에 실패했습니다.');
    } finally {
      setGenerating(false);
    }
  };

  if (!reports) return <div className="panel-empty">주간 리포트를 불러오는 중입니다.</div>;

  return (
    <section className="weekly-report-page">
      <div className="weekly-report-header">
        <div>
          <p className="page-eyebrow">WEEKLY INSIGHT</p>
          <h1>주간 분석</h1>
          <p>최근 7일간의 채점 결과를 바탕으로 학습 리포트를 만듭니다.</p>
        </div>
        {reports.length > 0 && (
          <button className="primary-btn" type="button" onClick={createReport} disabled={generating}>
            {generating ? '분석 중...' : '이번 주 리포트 만들기'}
          </button>
        )}
      </div>
      {error && <div className="weekly-report-error" role="alert">{error}</div>}
      {!reports.length ? (
        <div className="panel-empty weekly-report-empty">
          <p>아직 생성된 주간 분석이 없습니다.</p>
          <span>최근 7일 내 채점 결과가 있다면 첫 리포트를 만들어 보세요.</span>
          <button className="primary-btn" type="button" onClick={createReport} disabled={generating}>
            {generating ? '분석 중...' : '이번 주 리포트 만들기'}
          </button>
        </div>
      ) : (
        <div className="weekly-report-list">
          {reports.map((report) => (
            <button key={report.id} type="button" className="weekly-report-card" onClick={() => navigate(`/weekly-reports/${report.id}`)}>
              <div className="weekly-report-card-top">
                <span>{formatPeriod(report)}</span>
                <span>{report.review_count}문제 풀이</span>
              </div>
              <div className="weekly-report-score-preview">
                {report.skill_scores.map((score) => <span key={score.key}>{score.score}</span>)}
              </div>
              <p>{report.overall_skill_comment}</p>
              <strong>리포트 보기 →</strong>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
