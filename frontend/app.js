const API = 'http://127.0.0.1:8000';

let problems = [];
let selectedProblem = null;
let currentSession = null;
let currentResult = null;

const problemSelector = document.getElementById('problemSelector');
const problemTitle = document.getElementById('problemTitle');
const problemContent = document.getElementById('problemContent');
const problemRubric = document.getElementById('problemRubric');
const problemMeta = document.getElementById('problemMeta');
const sessionStatus = document.getElementById('sessionStatus');
const answerText = document.getElementById('answerText');
const wordCounter = document.getElementById('wordCounter');
const chatPanel = document.querySelector('.chat-panel');
const proofPanel = document.querySelector('.proof-panel');
const scoreCard = document.querySelector('.score-card');

function formatMeta(meta) {
  if (!meta) return '';
  const parts = [];
  if (meta.school) parts.push(meta.school);
  if (meta.exam_type) parts.push(meta.exam_type);
  if (meta.year) parts.push(meta.year);
  return parts.join(' · ');
}

function createOptionLabel(problem) {
  const school = problem.meta?.school || problem.source;
  const year = problem.meta?.year || '연도 미정';
  const type = problem.meta?.exam_type || '문제 유형';
  return `${school} (${type}) - ${year}`;
}

function updateWordCount() {
  const length = answerText.value.trim().length;
  wordCounter.textContent = `${length} / 1,000자`;
}

function clearScorePanels() {
  document.querySelectorAll('.score-number').forEach((el) => (el.textContent = '--'));
  document.querySelectorAll('.criteria-item .bar span').forEach((bar) => (bar.style.width = '0%'));
  document.querySelectorAll('.criteria-row span:last-child').forEach((node) => {
    if (node.textContent.includes('/')) node.textContent = '0 / 0';
  });
}

function renderProblemDetails() {
  if (!selectedProblem) {
    problemTitle.textContent = '문제를 선택해 주세요';
    problemContent.textContent = '선택한 문제의 본문과 지문이 이곳에 표시됩니다.';
    problemRubric.textContent = '문제를 선택하면 해당 문항과 채점 기준이 표시됩니다.';
    problemMeta.textContent = '';
    return;
  }

  problemTitle.textContent = selectedProblem.title;
  problemContent.textContent = selectedProblem.content;
  problemRubric.textContent = selectedProblem.rubric || '채점 기준 정보가 없습니다.';
  problemMeta.textContent = formatMeta(selectedProblem.meta);
}

function renderSessionStatus() {
  if (!currentSession) {
    sessionStatus.textContent = '세션이 아직 시작되지 않았습니다.';
  } else {
    sessionStatus.textContent = `세션 ${currentSession.id} 진행 중 · 선택 문제: ${selectedProblem?.title || '없음'}`;
  }
}

function renderScoreResult(result) {
  if (!result) {
    clearScorePanels();
    return;
  }
  const mainScore = document.querySelector('.score-number');
  if (mainScore) mainScore.textContent = result.score?.toString() || '0';
  document.querySelectorAll('.score-ring').forEach((ring) => {
    const pct = Math.min(100, Math.max(0, (result.score || 0)));
    ring.style.setProperty('--score', pct);
  });

  const criteriaItems = document.querySelectorAll('.criteria-item');
  result.scores?.forEach((item, idx) => {
    const row = criteriaItems[idx];
    if (!row) return;
    const ratio = item.total ? (item.value / item.total) * 100 : 0;
    const bar = row.querySelector('.bar span');
    if (bar) bar.style.width = `${ratio}%`;
    const labelSpan = row.querySelector('.criteria-row span:last-child');
    if (labelSpan) labelSpan.textContent = `${item.value} / ${item.total}`;
    const titleSpan = row.querySelector('.criteria-row span:first-child');
    if (titleSpan) titleSpan.textContent = item.label;
  });

  const scoreTitle = document.querySelector('.score-title');
  const scoreSub = document.querySelector('.score-sub');
  if (scoreTitle) scoreTitle.textContent = '실제 채점 결과';
  if (scoreSub) scoreSub.textContent = result.commentary || '채점 결과를 확인하세요.';
}

function renderProofItems(result) {
  const proofContainer = proofPanel.querySelector('.panel-inner');
  if (!proofContainer) return;
  const errors = result?.grammar_errors || [];
  if (!errors.length) {
    proofContainer.innerHTML = '<div class="proof-box"><div class="proof-tag">정보</div><div class="proof-text">채점 후 문법 및 첨삭 항목이 표시됩니다.</div></div>';
    return;
  }
  proofContainer.innerHTML = errors
    .slice(0, 3)
    .map((item) => `
      <div class="proof-box">
        <div class="proof-tag">${item.type || '문법'}</div>
        <div class="proof-text">${item.error}</div>
        <div class="proof-meta">${item.suggestion || '제안: 수정이 필요합니다.'}</div>
      </div>
    `)
    .join('');
}

function renderChatMessages(messages) {
  if (!chatPanel) return;
  chatPanel.innerHTML = messages
    .map((message) => `
      <div class="chat-box ${message.role === 'assistant' ? 'chat-assistant' : 'chat-user'}">
        <div class="chat-badge ${message.role === 'assistant' ? 'assistant' : ''}">${message.role === 'assistant' ? 'AI' : '교사'}</div>
        <div class="chat-msg">${message.text}</div>
      </div>
    `)
    .join('') + `
      <div class="chat-input-wrap">
        <input id="chatInput" type="text" placeholder="Tutor에게 질문하기" />
        <button id="btnSendChat" class="primary-btn small-btn">전송</button>
      </div>
    `;
  document.getElementById('btnSendChat').onclick = sendChat;
  document.getElementById('chatInput').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') sendChat();
  });
}

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
    problemSelector.innerHTML = problems
      .map((problem) => `<option value="${problem.id}">${createOptionLabel(problem)}</option>`)
      .join('');
    if (problems.length > 0) {
      selectedProblem = problems[0];
      renderProblemDetails();
    }
  } catch (err) {
    console.error(err);
    problemSelector.innerHTML = '<option>문제 로드 실패</option>';
  }
}

async function createSession() {
  if (!selectedProblem) {
    alert('먼저 문제를 선택하세요.');
    return;
  }
  try {
    currentSession = await fetchApi('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: 1, problem_id: selectedProblem.id, problem_source: selectedProblem.source }),
    });
    renderSessionStatus();
    alert(`세션 ${currentSession.id}이(가) 생성되었습니다.`);
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
    alert('답안이 저장되었습니다. 채점을 요청하세요.');
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
  try {
    const result = await fetchApi('/api/grade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: currentSession.id, source: 'ui' }),
    });
    currentResult = result;
    renderScoreResult(result);
    renderProofItems(result);
    const existingMessages = chatPanel.querySelectorAll('.chat-box');
    if (!existingMessages.length) {
      renderChatMessages([{ role: 'assistant', text: '채점이 완료되었습니다. Tutor와 질문을 주고받을 수 있습니다.' }]);
    }
  } catch (err) {
    console.error(err);
    alert('채점에 실패했습니다. 콘솔을 확인하세요.');
  }
}

async function sendChat() {
  const input = document.getElementById('chatInput');
  if (!input || !input.value.trim()) return;
  if (!currentSession) {
    alert('세션을 먼저 시작하세요.');
    return;
  }
  const text = input.value.trim();
  input.value = '';

  const currentMessages = [];
  chatPanel.querySelectorAll('.chat-box').forEach((node) => {
    const badge = node.querySelector('.chat-badge');
    const msg = node.querySelector('.chat-msg')?.textContent;
    if (!badge || !msg) return;
    currentMessages.push({ role: badge.textContent === 'AI' ? 'assistant' : 'user', text: msg });
  });

  currentMessages.push({ role: 'user', text });
  renderChatMessages(currentMessages);

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
  }
}

function onProblemChange() {
  const id = Number(problemSelector.value);
  selectedProblem = problems.find((problem) => problem.id === id);
  renderProblemDetails();
  renderSessionStatus();
}

function bindEvents() {
  document.getElementById('btnLoadProblems').onclick = loadProblems;
  document.getElementById('btnStartSession').onclick = createSession;
  document.getElementById('btnSubmitAnswer').onclick = saveAnswer;
  document.getElementById('btnGrade').onclick = gradeAnswer;
  problemSelector.onchange = onProblemChange;
  answerText.addEventListener('input', updateWordCount);
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
  await loadProblems();
  renderProblemDetails();
  renderSessionStatus();
  updateWordCount();
  healthCheck();
}

init();
