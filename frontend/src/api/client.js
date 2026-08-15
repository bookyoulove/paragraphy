const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

let accessToken = null;

function toProblem(problem) {
  return {
    id: problem.id,
    title: problem.title,
    content: problem.content,
    source: problem.created_by_user ? '직접 입력' : (problem.university ?? '등록 문제'),
    meta: {
      school: problem.university ?? (problem.created_by_user ? '직접 입력' : '등록 문제'),
      exam_type: problem.created_by_user ? '사용자 문제' : '논술 문제',
      year: problem.year?.toString() ?? '',
    },
    rubric: (problem.rubrics ?? [])
      .map((item) => [item.criteria, item.description].filter(Boolean).join(': '))
      .join('\n'),
    raw: problem,
  };
}

function toResult(result, answer, attempt = 1) {
  const scores = (result.criteria_scores ?? []).map((item) => ({
    label: item.criterion,
    value: item.score,
    maxScore: 5,
    rationale: item.rationale ?? '',
    improvement: item.improvement ?? '',
  }));
  const corrections = result.grammar_result?.revised_sentences ?? [];

  return {
    id: result.id,
    attempt,
    score: scores.reduce((total, item) => total + item.value, 0),
    totalMax: scores.length * 5,
    createdAt: result.created_at,
    answer,
    commentary: result.overall_comment ?? '',
    scores,
    errors: corrections.map((item) => ({
      type: '첨삭',
      before: item.origin,
      after: item.revised,
      note: 'AI가 제안한 문장 수정입니다.',
    })),
  };
}

function toSession(session) {
  const answers = session.user_answers ?? [];
  const latestAnswer = answers.at(-1);
  const results = answers
    .filter((item) => item.analysis_result)
    .map((item, index) => toResult(item.analysis_result, item.user_answer, index + 1));

  return {
    id: session.id,
    problem: toProblem(session.problem),
    answer: latestAnswer?.user_answer ?? '',
    answerId: latestAnswer?.id ?? null,
    results,
    createdAt: session.created_at,
  };
}

function parseRubrics(text) {
  const rows = text
    .split('\n')
    .map((row) => row.trim())
    .filter(Boolean);
  return (rows.length ? rows : ['논리적 주장과 근거 제시'])
    .map((row) => row.replace(/^\d+[.)]\s*/, ''))
    .map((row) => {
      const [criteria, ...description] = row.split(':');
      return { criteria: criteria.trim(), description: description.join(':').trim() || null };
    });
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers);
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok)
    throw new Error((await response.text()) || `API 요청 실패 (${response.status})`);
  return response.status === 204 ? null : response.json();
}

export const api = {
  async login(username, password) {
    const body = new URLSearchParams({ username, password });
    const response = await request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
    accessToken = response.access_token;
    return { identifier: username, token: response.access_token };
  },
  clearToken() {
    accessToken = null;
  },
  async getProblems() {
    return (await request('/problems/')).map(toProblem);
  },
  async generateRubric({ content }) {
    const rubrics = await request('/problems/rubric-gen', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, model_answer: null }),
    });
    return rubrics
      .map((item) => [item.criteria, item.description].filter(Boolean).join(': '))
      .join('\n');
  },
  async createProblem({ title, content, rubric }) {
    return toProblem(
      await request('/problems/custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content, model_answer: null, rubrics: parseRubrics(rubric) }),
      }),
    );
  },
  async createSession(problem) {
    return toSession(
      await request('/sessions/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ problem_id: problem.id }),
      }),
    );
  },
  async saveAnswer(session, answer) {
    const payload = { user_answer: answer, status: 'draft' };
    const response = session.answerId
      ? await request(`/sessions/${session.id}/answers/${session.answerId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      : await request(`/sessions/${session.id}/answers`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
    return { ...session, answer, answerId: response.answer_id };
  },
  async grade(session) {
    if (!session.answerId) throw new Error('답안을 먼저 저장해주세요.');
    const response = await request(`/sessions/${session.id}/answers/${session.answerId}/grading`);
    return toResult(response, session.answer, session.results.length + 1);
  },
  async getSessions() {
    return (await request('/sessions/')).map(toSession);
  },
  async getSession(sessionId) {
    return toSession(await request(`/sessions/${sessionId}`));
  },
};
