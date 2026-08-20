import { problems as initialProblems } from './data';

let nextProblemId = 3;
let nextSessionId = 101;
let problemStore = [...initialProblems];
const sessions = [];

const delay = (value, ms = 350) => new Promise((resolve) => setTimeout(() => resolve(value), ms));

export const mockApi = {
  getProblems: () => delay([...problemStore]),
  createProblem: ({ title, content, rubrics }) => {
    const problem = {
      id: nextProblemId++,
      title,
      content,
      rubric: rubrics?.length
        ? rubrics
        : [{ criteria: '논리적 주장과 근거 제시', description: null }],
      source: '직접 입력',
      meta: { school: '직접 입력', exam_type: '사용자 문제', year: '2026' },
    };
    problemStore = [...problemStore, problem];
    return delay(problem);
  },
  generateRubric: () =>
    delay([
      { criteria: '핵심 쟁점 파악', description: '문제의 핵심 쟁점을 정확히 파악한다.' },
      { criteria: '주장과 근거', description: '주장이 분명하고 근거가 적절하다.' },
      { criteria: '논리적 구조와 표현', description: '논리적 구조와 표현이 자연스럽다.' },
    ]),
  createSession: (problem) => {
    const session = {
      id: nextSessionId++,
      problem,
      answer: '',
      results: [],
      createdAt: new Date().toISOString(),
    };
    sessions.unshift(session);
    return delay(session, 150);
  },
  saveAnswer: (session, answer) => {
    session.answer = answer;
    return delay(session, 150);
  },
  grade: (session) => {
    const attempt = session.results.length + 1;
    const score = attempt === 1 ? 11 : 13;
    const result = {
      attempt,
      score,
      totalMax: 15,
      createdAt: new Date().toISOString(),
      answer: session.answer,
      commentary:
        '핵심 쟁점을 잘 포착했습니다. 근거 사이의 인과관계를 한 단계 더 구체화하면 설득력이 높아집니다.',
      scores: [
        {
          label: '쟁점 파악',
          value: 4,
          maxScore: 5,
          rationale: '문제의 핵심 쟁점을 정확히 짚었습니다.',
          improvement: '주장과 쟁점의 연결을 첫 문장에서 더 분명히 드러내 보세요.',
        },
        {
          label: '논리 전개',
          value: 3,
          maxScore: 5,
          rationale: '주장은 분명하지만 근거 사이의 인과관계가 다소 생략되어 있습니다.',
          improvement: '각 근거가 결론을 어떻게 뒷받침하는지 연결 문장을 추가해 보세요.',
        },
        {
          label: '근거와 표현',
          value: attempt === 1 ? 4 : 5,
          maxScore: 5,
          rationale: '사례 선택과 표현이 전반적으로 자연스럽습니다.',
          improvement: '반대 관점을 함께 검토하면 논증이 더욱 단단해집니다.',
        },
      ],
      suggestions: [
        '정책 대안이 어떤 문제를 해결하는지 연결해 보세요.',
        '반대 입장을 한 문단에서 검토하면 논증이 단단해집니다.',
      ],
      errors: [
        {
          type: '표현',
          before: '자원의 배분',
          after: '자원 배분',
          note: '조사 사용을 줄이면 문장이 더 간결해집니다.',
        },
      ],
    };
    session.results.push(result);
    return delay(result, 900);
  },
  getSessions: () => delay([...sessions]),
  chat: (question, result) =>
    delay(
      `좋은 질문이에요. ${result ? `현재 답안은 ${result.score}점으로, 특히 '${result.scores[1].label}' 항목을 보완하면 점수를 높일 수 있어요.` : '먼저 답안을 채점하면 결과를 바탕으로 자세히 설명해 드릴게요.'} 질문하신 '${question}'에 대해서는 근거와 결론 사이의 연결 문장을 추가해 보세요.`,
      500,
    ),
};
