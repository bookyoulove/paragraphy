import { buildComparisonModel } from '../utils/comparisonData';
import { formatWrittenAt } from '../utils/formatters';
import './CompareTable.css';

export default function CompareTable({
  results,
  onSelectRound,
  selectedAnswerId = null,
  truncate = true,
}) {
  const { columns, rows, hiddenMiddleCount } = buildComparisonModel(results, {
    truncate,
    selectedId: selectedAnswerId,
  });
  return (
    <div className="compare-table-wrap">
      {hiddenMiddleCount > 0 && (
        <p className="compare-truncation-note">
          … 표시된 구간은 중간 {hiddenMiddleCount}개 회차를 생략한 것입니다.
        </p>
      )}
      <table className="compare-table">
        <thead>
          <tr>
            <th>회차</th>
            {columns.map((item) =>
              item.isGap ? (
                <th
                  className="compare-gap-column"
                  key={item.id}
                  title={`중간 ${item.hiddenMiddleCount}개 회차 생략`}
                  aria-label={`중간 ${item.hiddenMiddleCount}개 회차 생략`}
                >
                  …
                </th>
              ) : (
                <th key={item.id}>
                  {onSelectRound ? (
                    <button
                      type="button"
                      className={`compare-attempt-btn ${
                        item.answerId === selectedAnswerId ? 'is-selected' : ''
                      }`}
                      onClick={() => onSelectRound(item.answerId)}
                    >
                      {item.name}
                    </button>
                  ) : (
                    <span className="compare-th-name">{item.name}</span>
                  )}
                  <span className="compare-th-date">{formatWrittenAt(item.answerCreatedAt)}</span>
                  {item.answerId === selectedAnswerId && (
                    <span className="compare-current-label">현재 선택</span>
                  )}
                </th>
              ),
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr className="compare-criteria-row" key={row.label}>
              <td>{row.label}</td>
              {row.values.map((score, index) =>
                columns[index].isGap ? (
                  <td className="compare-gap-column" key={`${row.label}-${columns[index].id}`}>
                    …
                  </td>
                ) : (
                  <td key={`${row.label}-${columns[index].id}`}>
                    {score ? `${score.value} / ${score.maxScore}` : '—'}
                  </td>
                ),
              )}
            </tr>
          ))}
          <tr className="compare-total">
            <td>총점</td>
            {columns.map((item) =>
              item.isGap ? (
                <td className="compare-gap-column" key={item.id}>
                  …
                </td>
              ) : (
                <td key={item.id}>
                  {item.score} / {item.totalMax}
                </td>
              ),
            )}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
