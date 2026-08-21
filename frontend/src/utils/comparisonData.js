import { selectDisplayedResults } from './formatters';

export const COMPARISON_LABEL_WIDTH = 180;
export const COMPARISON_ITEM_WIDTH = 150;

export function buildComparisonModel(results = [], { truncate = true } = {}) {
  const displayed = truncate ? selectDisplayedResults(results) : results;
  const hiddenMiddleCount = truncate ? Math.max(0, results.length - displayed.length) : 0;
  const hasHiddenMiddle = hiddenMiddleCount > 0;
  const columns = hasHiddenMiddle
    ? [
        displayed[0],
        { id: 'comparison-gap', isGap: true, hiddenMiddleCount },
        ...displayed.slice(1),
      ]
    : displayed;
  const criteria = [];
  const seenCriteria = new Set();

  displayed.forEach((result) => {
    (result.scores ?? []).forEach((score) => {
      if (!seenCriteria.has(score.label)) {
        seenCriteria.add(score.label);
        criteria.push(score.label);
      }
    });
  });

  const scoreMaps = displayed.map(
    (result) => new Map((result.scores ?? []).map((score) => [score.label, score])),
  );
  const scoreMapsByResultId = new Map(
    displayed.map((result, index) => [result.id, scoreMaps[index]]),
  );
  const rows = criteria.map((label) => ({
    label,
    values: columns.map((column) =>
      column.isGap ? null : (scoreMapsByResultId.get(column.id)?.get(label) ?? null),
    ),
  }));
  const chartData = displayed.map((result, index) => {
    const row = {
      attempt: result.name || `${index + 1}회차`,
      total: result.score,
    };
    criteria.forEach((label) => {
      row[label] = scoreMaps[index].get(label)?.value ?? 0;
    });
    return row;
  });

  if (hasHiddenMiddle) {
    const gapRow = { attempt: '…', isGap: true, total: null };
    criteria.forEach((label) => {
      gapRow[label] = null;
    });
    chartData.splice(1, 0, gapRow);
  }

  return { displayed, columns, criteria, rows, chartData, hiddenMiddleCount };
}
