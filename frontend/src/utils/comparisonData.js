import { selectDisplayedResults } from './formatters';

export const COMPARISON_LABEL_WIDTH = 180;
export const COMPARISON_ITEM_WIDTH = 150;

export function buildComparisonModel(results = [], { truncate = true, selectedId = null } = {}) {
  const displayed = truncate ? selectDisplayedResults(results, selectedId) : results;
  const hiddenMiddleCount = truncate ? Math.max(0, results.length - displayed.length) : 0;
  const resultIndexes = new Map(results.map((result, index) => [result.id, index]));
  const columns = [];
  let previousResultIndex = null;

  displayed.forEach((result, index) => {
    const resultIndex = resultIndexes.get(result.id);
    if (index > 0 && resultIndex > previousResultIndex + 1) {
      columns.push({
        id: `comparison-gap-${index}`,
        isGap: true,
        hiddenMiddleCount: resultIndex - previousResultIndex - 1,
      });
    }
    columns.push(result);
    previousResultIndex = resultIndex;
  });

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

  if (columns.some((column) => column.isGap)) {
    const chartGapRows = columns
      .map((column, index) => (column.isGap ? { index, column } : null))
      .filter(Boolean)
      .reverse();
    chartGapRows.forEach(({ index }) => {
      const gapRow = { attempt: '…', isGap: true, total: null };
      criteria.forEach((label) => {
        gapRow[label] = null;
      });
      const chartIndex = columns.slice(0, index).filter((item) => !item.isGap).length;
      chartData.splice(chartIndex, 0, gapRow);
    });
  }

  const maxTotalScore = Math.max(
    criteria.length * 5,
    ...displayed.map((result) => result.totalMax ?? 0),
    1,
  );

  return {
    displayed,
    columns,
    criteria,
    rows,
    chartData,
    hiddenMiddleCount,
    maxTotalScore,
  };
}
