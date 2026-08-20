import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

function formatPeriod(report) {
  const start = new Date(report.period_start);
  const end = new Date(report.period_end);
  return `${start.getMonth() + 1}.${start.getDate()} ~ ${end.getMonth() + 1}.${end.getDate()}`;
}

export default function WeeklyReportsPage({ user }) {
  const navigate = useNavigate();
  const [reports, setReports] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    api.getSkillReports().then(setReports).catch((err) => setError(err.message));
  }, [user]);

  if (error) return <div className="panel-empty">{error}</div>;
  if (!reports) return <div className="panel-empty">주간 리포트를 불러오는 중입니다.</div>;
  if (!reports.length) {
    return <div className="panel-empty">아직 생성된 주간 분석이 없습니다. 채점 결과가 쌓이면 리포트를 생성해 보세요.</div>;
  }

  return (
    <section className="weekly-report-page">
      <div className="weekly-report-header">
        <div>
          <p className="page-eyebrow">WEEKLY INSIGHT</p>
          <h1>주간 분석</h1>
          <p>저장된 주간 학습 리포트를 확인하세요.</p>
        </div>
      </div>
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
    </section>
  );
}
