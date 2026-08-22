const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');
const AUTH_STORAGE_KEY = 'paragraphy.auth';

function getWebSocketBaseUrl() {
  if (import.meta.env.DEV && typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}`;
  }

  return WS_BASE_URL;
}

function getAuthStorage() {
  return typeof window === 'undefined' ? null : window.sessionStorage;
}

function readStoredAuth() {
  const storage = getAuthStorage();
  if (!storage) return null;
  try {
    const auth = JSON.parse(storage.getItem(AUTH_STORAGE_KEY) ?? 'null');
    return auth?.identifier && auth?.token ? auth : null;
  } catch {
    return null;
  }
}

function storeAuth(auth) {
  getAuthStorage()?.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
}

function clearStoredAuth() {
  getAuthStorage()?.removeItem(AUTH_STORAGE_KEY);
}

const storedAuth = readStoredAuth();
let accessToken = storedAuth?.token ?? null;

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

function getHelpFields(help) {
  return {
    note: help?.comment ?? '',
    examples: help?.examples ?? [],
    ruleArticle: help?.rule_article ?? '',
  };
}

function deriveCorrections(grammarResult) {
  const helps = grammarResult?.helps ?? {};
  const helpEntries = Object.values(helps);
  const corrections = (grammarResult?.revised_blocks ?? []).flatMap((block) => {
    if (block.origin === block.revised) return [];
    const revisions = block.revisions?.length ? block.revisions : [{ revised: block.revised }];
    return revisions.map((revision) => {
      const help = revision.help_id
        ? (helps[revision.help_id] ?? helpEntries.find((item) => item.id === revision.help_id))
        : null;
      return {
        type: '첨삭',
        before: block.origin,
        after: revision.revised ?? block.revised,
        ...getHelpFields(help),
      };
    });
  });

  const referencedHelpIds = new Set(
    (grammarResult?.revised_blocks ?? []).flatMap((block) =>
      (block.revisions ?? []).map((revision) => revision.help_id),
    ),
  );
  const sentenceHelpCandidates = helpEntries.filter((help) => !referencedHelpIds.has(help.id));
  const sentenceHelp =
    sentenceHelpCandidates.length === 1
      ? sentenceHelpCandidates[0]
      : helpEntries.length === 1
        ? helpEntries[0]
        : null;

  const sentenceCorrections = (grammarResult?.revised_sentences ?? [])
    .filter((item) => item.origin !== item.revised)
    .map((item) => ({
      type: '첨삭',
      before: item.origin,
      after: item.revised,
      ...getHelpFields(sentenceHelp),
    }));

  if (corrections.length) return corrections;
  return sentenceCorrections;
}

function toResult(result, answerMeta) {
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
    answerId: answerMeta.id,
    name: answerMeta.name,
    answerCreatedAt: answerMeta.created_at,
    score: scores.reduce((total, item) => total + item.value, 0),
    totalMax: scores.length * 5,
    createdAt: result.created_at,
    answer: answerMeta.user_answer,
    commentary: result.overall_comment ?? '',
    scores,
    errors: corrections,
  };
}

function toSession(session) {
  const rawAnswers = session.user_answers ?? [];
  const latestAnswer = rawAnswers.at(-1);
  const results = rawAnswers
    .filter((item) => item.analysis_result)
    .map((item) => toResult(item.analysis_result, item));
  const answers = rawAnswers.map((item) => ({
    id: item.id,
    name: item.name,
    createdAt: item.created_at,
    status: item.status,
    userAnswer: item.user_answer,
    result: item.analysis_result ? toResult(item.analysis_result, item) : null,
  }));

  return {
    id: session.id,
    problem: toProblem(session.problem),
    answer: latestAnswer?.user_answer ?? '',
    answerId: latestAnswer?.id ?? null,
    answerName: latestAnswer?.name ?? '',
    answerCreatedAt: latestAnswer?.created_at ?? null,
    answerSubmitted: Boolean(latestAnswer?.analysis_result),
    answers,
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
    if (response.status === 401) {
      accessToken = null;
      clearStoredAuth();
      window.dispatchEvent(new Event('paragraphy:auth-expired'));
    }
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
    const auth = { identifier: username, token: response.access_token };
    storeAuth(auth);
    return auth;
  },
  getStoredUser() {
    const auth = readStoredAuth();
    return auth ? { identifier: auth.identifier, token: auth.token } : null;
  },
  clearToken() {
    accessToken = null;
    clearStoredAuth();
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
  async recommendProblems(keyword) {
    return request('/problems/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keyword }),
    });
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
  async deleteProblem(problemId) {
    await request(`/problems/${problemId}`, { method: 'DELETE' });
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
  async saveAnswer(session, answer, { createNew = false, name } = {}) {
    const useExisting = !createNew && session.answerId;
    const payload = { user_answer: answer, status: 'draft', name: name?.trim() || null };
    const response = useExisting
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
    const answerId = response.answer_id;
    const answerName = response.name;
    const answerCreatedAt = useExisting ? session.answerCreatedAt : response.created_at;
    const answers = useExisting
      ? session.answers.map((item) =>
          item.id === answerId ? { ...item, name: answerName, userAnswer: answer } : item,
        )
      : [
          ...session.answers,
          {
            id: answerId,
            name: answerName,
            createdAt: answerCreatedAt,
            status: 'draft',
            userAnswer: answer,
            result: null,
          },
        ];
    return {
      ...session,
      answer,
      answerId,
      answerName,
      answerCreatedAt,
      answerSubmitted: false,
      answers,
    };
  },
  async grade(session) {
    if (!session.answerId) throw new Error('답안을 먼저 저장해주세요.');
    const response = await request(`/sessions/${session.id}/answers/${session.answerId}/grading`);
    return toResult(response, {
      id: session.answerId,
      name: session.answerName,
      created_at: session.answerCreatedAt,
      user_answer: session.answer,
    });
  },
  async renameAnswer(sessionId, answerId, name) {
    const response = await request(`/sessions/${sessionId}/answers/${answerId}/name`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    return response.name;
  },
  async deleteAnswer(sessionId, answerId) {
    await request(`/sessions/${sessionId}/answers/${answerId}`, { method: 'DELETE' });
  },
  async deleteSession(sessionId) {
    await request(`/sessions/${sessionId}`, { method: 'DELETE' });
  },
  async getSessions() {
    return (await request('/sessions/')).map(toSession);
  },
  async getSession(sessionId) {
    return toSession(await request(`/sessions/${sessionId}`));
  },
  async getRanking(resultId) {
    return request(`/results/${resultId}/ranking`);
  },
  async getSkillReports() {
    return request('/skill-reports/');
  },
  async getSkillReport(reportId) {
    return request(`/skill-reports/${reportId}`);
  },
  async createWeeklySkillReport() {
    return request('/skill-reports/weekly', { method: 'POST' });
  },
  async sendSkillReportEmail(reportId, recipientEmail) {
    return request(`/skill-reports/${reportId}/email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipient_email: recipientEmail }),
    });
  },
  async generateProblemFromReport(reportId) {
    return toProblem(
      await request(`/skill-reports/${reportId}/generated-problem`, { method: 'POST' }),
    );
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
  // 스트리밍 + 가드레일 Tutor Chat WS 엔드포인트. 브라우저 WebSocket 핸드셰이크는
  // 커스텀 헤더를 못 실으므로 토큰을 쿼리 파라미터로 붙인다(서버가 동일하게 파싱).
  chatSocketUrl(resultId) {
    const token = accessToken ?? '';
    return `${getWebSocketBaseUrl()}/results/${resultId}/chat/ws?token=${encodeURIComponent(token)}`;
  },
};
