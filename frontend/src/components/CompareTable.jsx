import { formatWrittenAt } from '../utils/formatters';
import { buildComparisonModel } from '../utils/comparisonData';

export default function CompareTable({ results, onSelectRound }) {
  const { displayed, rows } = buildComparisonModel(results);
  return (
    <div className="compare-table-wrap">
      <table className="compare-table">
        <thead>
          <tr>
            <th>회차</th>
            {displayed.map((item) => (
              <th key={item.id}>
                {onSelectRound ? (
                  <button
                    type="button"
                    className="compare-attempt-btn"
                    onClick={() => onSelectRound(item.answerId)}
                  >
                    {item.name}
                  </button>
                ) : (
                  <span className="compare-th-name">{item.name}</span>
                )}
                <span className="compare-th-date">{formatWrittenAt(item.answerCreatedAt)}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr className="compare-criteria-row" key={row.label}>
              <td>{row.label}</td>
              {row.values.map((score, index) => (
                <td key={`${row.label}-${displayed[index].id}`}>
                  {score ? `${score.value} / ${score.maxScore}` : '—'}
                </td>
              ))}
            </tr>
          ))}
          <tr className="compare-total">
            <td>총점</td>
            {displayed.map((item) => (
              <td key={item.id}>
                {item.score} / {item.totalMax}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
