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
    rubric: problem.rubrics ?? [],
    raw: problem,
  };
}

function deriveCorrections(grammarResult) {
  const helps = grammarResult?.helps ?? {};
  const corrections = (grammarResult?.revised_blocks ?? []).flatMap((block) => {
    if (block.origin === block.revised) return [];
    const revisions = block.revisions?.length ? block.revisions : [{ revised: block.revised }];
    return revisions.map((revision) => {
      const help = revision.help_id ? helps[revision.help_id] : null;
      return {
        type: '첨삭',
        before: block.origin,
        after: revision.revised ?? block.revised,
        note: help?.comment ?? '',
        examples: help?.examples ?? [],
        ruleArticle: help?.rule_article ?? '',
      };
    });
  });

  if (corrections.length) return corrections;
  return (grammarResult?.revised_sentences ?? [])
    .filter((item) => item.origin !== item.revised)
    .map((item) => ({
      type: '첨삭',
      before: item.origin,
      after: item.revised,
      note: '',
      examples: [],
      ruleArticle: '',
    }));
}

function toResult(result, answer, attempt = 1) {
  const scores = (result.criteria_scores ?? []).map((item) => ({
    label: item.criterion,
    value: item.score,
    maxScore: 5,
    rationale: item.rationale ?? '',
    improvement: item.improvement ?? '',
  }));
  const corrections = deriveCorrections(result.grammar_result);

  return {
    id: result.id,
    attempt,
    score: scores.reduce((total, item) => total + item.value, 0),
    totalMax: scores.length * 5,
    createdAt: result.created_at,
    answer,
    commentary: result.overall_comment ?? '',
    scores,
    errors: corrections,
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

function toRubricPayload(rubrics) {
  const items = (Array.isArray(rubrics) ? rubrics : [])
    .map((item) => ({
      criteria: item.criteria?.trim() ?? '',
      description: item.description?.trim() || null,
    }))
    .filter((item) => item.criteria);
  return items.length ? items : [{ criteria: '논리적 주장과 근거 제시', description: null }];
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers);
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    const error = new Error('서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.');
    error.code = 'NETWORK_ERROR';
    throw error;
  }

  if (!response.ok) {
    const message =
      response.status === 401
        ? '로그인이 만료되었거나 인증이 필요합니다.'
        : response.status === 403
          ? '이 요청을 수행할 권한이 없습니다.'
          : response.status === 404
            ? '요청한 데이터를 찾을 수 없습니다.'
            : response.status >= 500
              ? '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
              : '요청을 처리하지 못했습니다. 입력 내용을 확인해주세요.';
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) return null;

  try {
    return await response.json();
  } catch {
    const error = new Error('서버에서 올바르지 않은 응답을 받았습니다.');
    error.status = response.status;
    throw error;
  }
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
    return rubrics;
  },
  async createProblem({ title, content, rubrics }) {
    return toProblem(
      await request('/problems/custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          content,
          model_answer: null,
          rubrics: toRubricPayload(rubrics),
        }),
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
  async saveAnswer(session, answer, { createNew = false } = {}) {
    const payload = { user_answer: answer, status: 'draft' };
    const response = !createNew && session.answerId
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
  async getChat(resultId) {
    try {
      const messages = await request(`/results/${resultId}/chat`);
      return messages.map((message) => ({
        id: message.id,
        role: message.role,
        text: message.content,
      }));
    } catch (error) {
      if (error.status === 404) return [];
      throw error;
    }
  },
  async chat(resultId, content) {
    const response = await request(`/results/${resultId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    if (response.error) throw new Error(response.error);
    return response.reply;
  },
};
