function resolveApiBase() {
  const { protocol, hostname, host, pathname } = window.location;
  if (hostname === '127.0.0.1' || hostname === 'localhost') {
    return 'http://127.0.0.1:8000';
  }
  // Elice VS Code tunnel proxy pattern: https://<id>.tunnel.elice.io/proxy/<port>/...
  const match = pathname.match(/\/proxy\/\d+\//);
  if (match) {
    const prefix = pathname.slice(0, match.index);
    return `${protocol}//${host}${prefix}/proxy/8000`;
  }
  return 'http://127.0.0.1:8000';
}

const API = resolveApiBase();
const USER_STORAGE_KEY = 'paragraphy_user';

let problems = [];
let selectedProblem = null;
let currentSession = null;
let currentErrors = [];
let currentUser = null;

const problemList = document.getElementById('problemList');
const problemTitle = document.getElementById('problemTitle');
const problemContent = document.getElementById('problemContent');
const problemRubric = document.getElementById('problemRubric');
const problemBody = document.getElementById('problemBody');
const btnToggleProblem = document.getElementById('btnToggleProblem');
const sessionStatus = document.getElementById('sessionStatus');
const answerText = document.getElementById('answerText');
const answerHighlight = document.getElementById('answerHighlight');
const wordCounter = document.getElementById('wordCounter');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const loginOverlay = document.getElementById('loginOverlay');
const userLabel = document.getElementById('userLabel');

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function formatMeta(meta) {
  if (!meta) return '';
  const parts = [];
  if (meta.school) parts.push(meta.school);
  if (meta.exam_type) parts.push(meta.exam_type);
  if (meta.year) parts.push(meta.year);
  return parts.join(' · ');
}

function cardLabel(problem) {
  const school = problem.meta?.school || problem.source;
  const type = problem.meta?.exam_type || '문제';
  const year = problem.meta?.year;
  return { title: problem.title, meta: [school, type, year].filter(Boolean).join(' · ') };
}

// ---------- 로그인 ----------
function loadStoredUser() {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (err) {
    return null;
  }
}

function saveStoredUser(user) {
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

function showLogin() {
  loginOverlay.hidden = false;
  document.getElementById('loginInput').focus();
}

function hideLogin() {
  loginOverlay.hidden = true;
}

async function doLogin() {
  const input = document.getElementById('loginInput');
  const errorBox = document.getElementById('loginError');
  const identifier = input.value.trim();
  if (!identifier) {
    errorBox.textContent = '식별자를 입력해주세요.';
    return;
  }
  try {
    const user = await fetchApi('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier }),
    });
    currentUser = user;
    saveStoredUser(user);
    userLabel.textContent = user.identifier;
    hideLogin();
    errorBox.textContent = '';
  } catch (err) {
    console.error(err);
    errorBox.textContent = '로그인에 실패했습니다. 백엔드 연결을 확인하세요.';
  }
}

function switchUser() {
  localStorage.removeItem(USER_STORAGE_KEY);
  currentUser = null;
  currentSession = null;
  renderSessionStatus();
  showLogin();
}

// ---------- 탭 전환 (채점결과/첨삭/챗봇) ----------
function bindTabs() {
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('active', t === tab));
      document.querySelectorAll('.tab-panel').forEach((p) => p.classList.toggle('active', p.dataset.panel === target));
    });
  });
}

// ---------- 문제 선택 모드 (기존 문제 / 직접 입력) ----------
function bindModeTabs() {
  document.querySelectorAll('.mode-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.mode;
      document.querySelectorAll('.mode-tab').forEach((t) => t.classList.toggle('active', t === tab));
      document.querySelectorAll('.mode-panel').forEach((p) => p.classList.toggle('active', p.dataset.modePanel === target));
    });
  });
}

// ---------- 답안 하이라이트 오버레이 ----------
function rebuildHighlight() {
  const text = answerText.value;
  if (!currentErrors.length) {
    answerHighlight.innerHTML = escapeHtml(text);
    return;
  }
  let html = escapeHtml(text);
  const seen = new Set();
  currentErrors.forEach((err) => {
    const before = (err.before || '').trim();
    if (!before || seen.has(before)) return;
    seen.add(before);
    const escaped = escapeHtml(before);
    if (html.includes(escaped)) {
      html = html.replace(escaped, `<mark>${escaped}</mark>`);
    }
  });
  answerHighlight.innerHTML = html;
}

function syncHighlightScroll() {
  answerHighlight.scrollTop = answerText.scrollTop;
  answerHighlight.scrollLeft = answerText.scrollLeft;
}

function updateWordCount() {
  const length = answerText.value.trim().length;
  wordCounter.textContent = `${length}자`;
}

// ---------- 문제 렌더 ----------
function renderProblemList() {
  if (!problems.length) {
    problemList.innerHTML = '<div class="panel-empty">등록된 문제가 없습니다.</div>';
    return;
  }
  problemList.innerHTML = problems
    .map((problem) => {
      const { title, meta } = cardLabel(problem);
      const selected = selectedProblem && selectedProblem.id === problem.id;
      return `
        <button type="button" class="problem-card ${selected ? 'selected' : ''}" data-problem-id="${problem.id}">
          <span class="card-title">${escapeHtml(title)}</span>
          <span class="card-meta">${escapeHtml(meta)}</span>
        </button>
      `;
    })
    .join('');
  problemList.querySelectorAll('.problem-card').forEach((card) => {
    card.addEventListener('click', () => {
      const id = Number(card.dataset.problemId);
      selectProblem(problems.find((p) => p.id === id));
    });
  });
}

function selectProblem(problem) {
  selectedProblem = problem;
  renderProblemList();
  renderProblemDetails();
  renderSessionStatus();
}

function renderProblemDetails() {
  if (!selectedProblem) {
    problemTitle.textContent = '문제를 선택해 주세요';
    problemContent.textContent = '선택한 문제의 본문과 지문이 이곳에 표시됩니다.';
    problemRubric.textContent = '문제를 선택하면 해당 문항과 채점 기준이 표시됩니다.';
    return;
  }

  problemTitle.textContent = selectedProblem.title;
  problemContent.textContent = selectedProblem.content;
  problemRubric.textContent = selectedProblem.rubric || '채점 기준 정보가 없습니다.';
}

function renderSessionStatus() {
  if (!currentSession) {
    sessionStatus.textContent = '세션이 아직 시작되지 않았습니다.';
  } else {
    sessionStatus.textContent = `세션 ${currentSession.id} 진행 중 · 선택 문제: ${selectedProblem?.title || '없음'}`;
  }
}

// ---------- 채점 결과 렌더 ----------
function renderScoreResult(result) {
  const empty = document.getElementById('gradeEmpty');
  const content = document.getElementById('gradeContent');
  empty.hidden = true;
  content.hidden = false;

  const pct = result.total_max ? Math.round((result.score / result.total_max) * 100) : 0;
  document.getElementById('scoreRing').style.setProperty('--score', Math.min(100, Math.max(0, pct)));
  document.getElementById('scoreNumber').textContent = result.score;
  document.getElementById('scoreDivider').textContent = `/ ${result.total_max}`;
  document.getElementById('scoreTitle').textContent = `${selectedProblem?.source || ''} 채점 기준 적용`.trim();
  document.getElementById('scoreSub').textContent = result.commentary || '';

  const criteriaList = document.getElementById('criteriaList');
  criteriaList.innerHTML = (result.scores || [])
    .map((item) => {
      const ratio = item.max_score ? (item.value / item.max_score) * 100 : 0;
      return `
        <div class="criteria-item">
          <div class="criteria-row"><span>${escapeHtml(item.label)}</span><span>${item.value} / ${item.max_score}</span></div>
          <div class="bar"><span style="width:${ratio}%"></span></div>
        </div>
      `;
    })
    .join('');

  const suggestionList = document.getElementById('suggestionList');
  suggestionList.innerHTML = (result.suggestions || []).map((s) => `<li>${escapeHtml(s)}</li>`).join('') || '<li>추가 제안이 없습니다.</li>';
}

function tagClassForType(type) {
  if (type.includes('비약') || type.includes('논리') || type.includes('단정')) return 'neutral';
  if (type.includes('어색') || type.includes('표현') || type.includes('중복')) return 'warning';
  return '';
}

function renderProofItems(result) {
  const errors = result?.grammar_errors || [];
  currentErrors = errors;
  document.getElementById('proofCount').textContent = errors.length
    ? `감지된 오류 ${errors.length}건 · 어문규정(Bareun) + 첨삭 Agent`
    : '';
  const proofList = document.getElementById('proofList');
  if (!errors.length) {
    proofList.innerHTML = '<div class="proof-box"><div class="proof-tag">정보</div><div class="proof-text">감지된 첨삭 항목이 없습니다.</div></div>';
    rebuildHighlight();
    return;
  }
  proofList.innerHTML = errors
    .map(
      (item) => `
      <div class="proof-box">
        <div class="proof-tag ${tagClassForType(item.type || '')}">${escapeHtml(item.type || '표현')}</div>
        <div class="proof-text"><del>${escapeHtml(item.before || '')}</del> → ${escapeHtml(item.after || '')}</div>
        <div class="proof-meta">${escapeHtml(item.note || '')}</div>
      </div>
    `
    )
    .join('');
  rebuildHighlight();
}

// ---------- 채팅 ----------
function renderChatMessages(messages) {
  chatMessages.innerHTML = messages
    .map(
      (message) => `
      <div class="chat-box ${message.role === 'assistant' ? 'chat-assistant' : 'chat-user'}">
        <div class="chat-badge ${message.role === 'assistant' ? 'assistant' : ''}">${message.role === 'assistant' ? 'AI' : '나'}</div>
        <div class="chat-msg">${escapeHtml(message.text)}</div>
      </div>
    `
    )
    .join('');
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ---------- API 호출 ----------
async function fetchApi(path, options = {}) {
  const res = await fetch(`${API}${path}`, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

async function loadProblems() {
  try {
    problems = await fetchApi('/api/problems');
    renderProblemList();
    if (!selectedProblem && problems.length > 0) {
      selectProblem(problems[0]);
    }
  } catch (err) {
    console.error(err);
    problemList.innerHTML = '<div class="panel-empty">문제 로드 실패 — 백엔드 연결을 확인하세요.</div>';
  }
}

async function createSession() {
  if (!currentUser) {
    alert('먼저 로그인하세요.');
    return;
  }
  if (!selectedProblem) {
    alert('먼저 문제를 선택하세요.');
    return;
  }
  try {
    currentSession = await fetchApi('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: currentUser.id, problem_id: selectedProblem.id, problem_source: selectedProblem.source }),
    });
    renderSessionStatus();
  } catch (err) {
    console.error(err);
    alert('세션 생성에 실패했습니다. 콘솔을 확인하세요.');
  }
}

async function saveAnswer() {
  if (!currentSession) {
    alert('세션을 먼저 시작하세요.');
    return;
  }
  const text = answerText.value.trim();
  if (!text) {
    alert('답안을 입력하세요.');
    return;
  }
  try {
    await fetchApi('/api/answers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: currentSession.id, text, status: 'draft' }),
    });
  } catch (err) {
    console.error(err);
    alert('답안 저장에 실패했습니다. 콘솔을 확인하세요.');
  }
}

async function gradeAnswer() {
  if (!currentSession) {
    alert('세션을 먼저 시작하고 답안을 저장하세요.');
    return;
  }
  const btnGrade = document.getElementById('btnGrade');
  btnGrade.disabled = true;
  btnGrade.textContent = '채점 중...';
  try {
    await saveAnswer();
    const result = await fetchApi('/api/grade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: currentSession.id, source: 'ui' }),
    });
    renderScoreResult(result);
    renderProofItems(result);
    document.querySelector('.tab[data-tab="grade"]').click();
  } catch (err) {
    console.error(err);
    alert('채점에 실패했습니다. 콘솔을 확인하세요.');
  } finally {
    btnGrade.disabled = false;
    btnGrade.textContent = '채점 요청';
  }
}

async function sendChat() {
  if (!chatInput.value.trim()) return;
  if (!currentSession) {
    alert('세션을 먼저 시작하세요.');
    return;
  }
  const text = chatInput.value.trim();
  chatInput.value = '';

  const existing = [...chatMessages.querySelectorAll('.chat-box')].map((node) => ({
    role: node.classList.contains('chat-assistant') ? 'assistant' : 'user',
    text: node.querySelector('.chat-msg')?.textContent || '',
  }));
  existing.push({ role: 'user', text });
  renderChatMessages(existing);

  const btnSend = document.getElementById('btnSendChat');
  btnSend.disabled = true;
  try {
    const response = await fetchApi('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: currentSession.id, text }),
    });
    renderChatMessages(response.messages);
  } catch (err) {
    console.error(err);
    alert('Tutor 응답을 받는 데 실패했습니다. 콘솔을 확인하세요.');
  } finally {
    btnSend.disabled = false;
  }
}

// ---------- 직접 입력 + Rubric Agent ----------
async function generateRubric() {
  const title = document.getElementById('customTitle').value.trim();
  const content = document.getElementById('customContent').value.trim();
  const rubricBox = document.getElementById('customRubric');
  const status = document.getElementById('rubricStatus');
  if (!content) {
    alert('먼저 문제 본문을 입력하세요.');
    return;
  }
  const btn = document.getElementById('btnGenerateRubric');
  btn.disabled = true;
  status.textContent = 'AI가 채점 기준을 생성하는 중입니다...';
  try {
    const result = await fetchApi('/api/rubric/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content }),
    });
    rubricBox.value = result.rubric;
    status.textContent = 'AI가 생성한 채점 기준입니다. 필요하면 자유롭게 수정한 뒤 저장하세요.';
  } catch (err) {
    console.error(err);
    status.textContent = '채점 기준 생성에 실패했습니다. 콘솔을 확인하세요.';
  } finally {
    btn.disabled = false;
  }
}

async function createCustomProblem() {
  const title = document.getElementById('customTitle').value.trim();
  const content = document.getElementById('customContent').value.trim();
  const rubric = document.getElementById('customRubric').value.trim();
  if (!title || !content) {
    alert('문제 제목과 본문을 입력하세요.');
    return;
  }
  if (!rubric) {
    const proceed = confirm('채점 기준이 비어 있습니다. AI가 생성한 채점 기준 없이 저장할까요? (채점 시 정확도가 떨어질 수 있습니다)');
    if (!proceed) return;
  }
  const btn = document.getElementById('btnCreateProblem');
  btn.disabled = true;
  try {
    const problem = await fetchApi('/api/problems', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content, rubric: rubric || null, created_by: currentUser?.id || null }),
    });
    await loadProblems();
    selectProblem(problems.find((p) => p.id === problem.id) || problem);
    document.querySelector('.mode-tab[data-mode="existing"]').click();
    document.getElementById('customTitle').value = '';
    document.getElementById('customContent').value = '';
    document.getElementById('customRubric').value = '';
    document.getElementById('rubricStatus').textContent = '';
  } catch (err) {
    console.error(err);
    alert('문제 저장에 실패했습니다. 콘솔을 확인하세요.');
  } finally {
    btn.disabled = false;
  }
}

function bindEvents() {
  document.getElementById('btnLoadProblems').onclick = loadProblems;
  document.getElementById('btnStartSession').onclick = createSession;
  document.getElementById('btnSubmitAnswer').onclick = saveAnswer;
  document.getElementById('btnGrade').onclick = gradeAnswer;
  document.getElementById('btnSendChat').onclick = sendChat;
  document.getElementById('btnLogin').onclick = doLogin;
  document.getElementById('loginInput').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') doLogin();
  });
  document.getElementById('btnSwitchUser').onclick = switchUser;
  document.getElementById('btnGenerateRubric').onclick = generateRubric;
  document.getElementById('btnCreateProblem').onclick = createCustomProblem;
  chatInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') sendChat();
  });
  answerText.addEventListener('input', () => {
    updateWordCount();
    currentErrors = [];
    rebuildHighlight();
  });
  answerText.addEventListener('scroll', syncHighlightScroll);
  btnToggleProblem.onclick = () => {
    const collapsed = problemBody.classList.toggle('collapsed');
    btnToggleProblem.textContent = collapsed ? '펼치기' : '접기';
  };
  bindTabs();
  bindModeTabs();
}

async function healthCheck() {
  try {
    const res = await fetch(`${API}/health`);
    const data = await res.json();
    const status = document.querySelector('.topbar-meta');
    if (status) status.textContent = `대입 논술 채점 · 첨삭 · ${data.environment || 'online'}`;
  } catch (err) {
    console.error('Backend not ready yet', err);
    const status = document.querySelector('.topbar-meta');
    if (status) status.textContent = '대입 논술 채점 · 첨삭 · 백엔드 연결 실패';
  }
}

async function init() {
  bindEvents();
  const storedUser = loadStoredUser();
  if (storedUser) {
    currentUser = storedUser;
    userLabel.textContent = storedUser.identifier;
    hideLogin();
  } else {
    showLogin();
  }
  await loadProblems();
  renderSessionStatus();
  updateWordCount();
  rebuildHighlight();
  healthCheck();
}

init();
