export default function HistoryView({ sessions, compareOnly, onResume }) {
  const list = compareOnly ? sessions.filter((session) => session.results.length >= 2) : sessions;
  const message = compareOnly
    ? '아직 2회 이상 채점된 문제가 없습니다.'
    : '아직 작성한 답안이 없습니다. 문제를 선택해 답안을 작성해보세요.';
  return (
    <div className="picker-view">
      <div className="picker-view-header">
        <div>
          <div className="label-title">{compareOnly ? '채점 비교' : '답안 기록'}</div>
          <div className="label-sub">
            {compareOnly
              ? '2회 이상 채점한 문제를 확인합니다.'
              : '작성한 답안을 다시 열어 이어서 수정하고 재채점할 수 있습니다.'}
          </div>
        </div>
      </div>
      <div className="history-list">
        {list.length ? (
          list.map((session) => {
            const result = session.results.at(-1);
            return (
              <button className="history-card" key={session.id} onClick={() => onResume(session)}>
                <div className="history-card-main">
                  <div className="history-card-title">{session.problem.title}</div>
                  <div className="history-card-meta">
                    {session.problem.source} · 샘플 세션 #{session.id}
                  </div>
                </div>
                <span className={`history-card-score ${result ? '' : 'pending'}`}>
                  {result ? `${result.score} / ${result.totalMax}` : '미채점'}
                </span>
              </button>
            );
          })
        ) : (
          <div className="panel-empty">{message}</div>
        )}
      </div>
    </div>
  );
}
