import { formatWrittenAt, selectDisplayedResults } from '../utils/formatters';

export default function CompareTable({ results, onSelectRound }) {
  const displayed = selectDisplayedResults(results);
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
