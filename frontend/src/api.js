const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : `요청 실패 (${res.status})`
    throw new Error(message)
  }
  return body
}

export const api = {
  listProblems: (university) =>
    request(`/api/problems${university ? `?university=${encodeURIComponent(university)}` : ''}`),
  getProblem: (id) => request(`/api/problems/${id}`),
  suggestRubric: (payload) => request('/api/problems/rubric', { method: 'POST', body: JSON.stringify(payload) }),
  grade: (payload) => request('/api/grading', { method: 'POST', body: JSON.stringify(payload) }),
  feedback: (payload) => request('/api/feedback', { method: 'POST', body: JSON.stringify(payload) }),
  listSessions: (userIdentifier) => request(`/api/sessions?user_identifier=${encodeURIComponent(userIdentifier)}`),
  getSession: (sessionId) => request(`/api/sessions/${sessionId}`),
}

export const WS_BASE = API_BASE.replace(/^http/, 'ws')
