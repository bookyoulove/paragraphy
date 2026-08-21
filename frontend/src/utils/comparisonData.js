import { selectDisplayedResults } from './formatters';

export function buildComparisonModel(results = []) {
  const displayed = selectDisplayedResults(results);
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
  const rows = criteria.map((label) => ({
    label,
    values: scoreMaps.map((scoreMap) => scoreMap.get(label) ?? null),
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

  return { displayed, criteria, rows, chartData };
}
