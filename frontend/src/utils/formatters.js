export function formatWrittenAt(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  const pad = (value) => String(value).padStart(2, '0');
  const y = date.getFullYear();
  const m = pad(date.getMonth() + 1);
  const d = pad(date.getDate());
  const h = pad(date.getHours());
  const min = pad(date.getMinutes());
  return `(${y}-${m}-${d}, ${h}:${min} 작성)`;
}

export function formatCreatedAt(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function selectDisplayedResults(results, selectedId = null) {
  if (results.length <= 5) return results;
  const latest = results.slice(-4);
  const selectedIndex = results.findIndex(
    (result) => result.id === selectedId || result.answerId === selectedId,
  );
  const selectedIsVisible = selectedIndex === 0 || selectedIndex >= results.length - 4;
  if (selectedIndex === -1 || selectedIsVisible) return [results[0], ...latest];

  return [results[0], results[selectedIndex], ...results.slice(-3)];
}
