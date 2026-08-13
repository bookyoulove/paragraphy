// 채점 기준 설명에 원본 문서에서 그대로 옮겨온 "[원배점 N점]" 표기나 마크다운 강조(**)가
// 섞여 있을 때가 있다 — 화면엔 5점 척도 정책만 보이면 되므로 표시 직전에 걷어낸다.
export function cleanRubricText(text) {
  if (!text) return text
  return text
    .replace(/\[원배점[^\]]*\]/g, '')
    .replace(/\*\*/g, '')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

export function formatDateTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
