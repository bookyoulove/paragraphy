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
let hasGradedInSession = false;
let isGrading = false;
let previewingAttempt = null;
let savedDraftBeforePreview = null;

const landingView = document.getElementById('landingView');
const loginOverlay = document.getElementById('loginOverlay');
const pageWrap = document.getElementById('pageWrap');
const userLabel = document.getElementById('userLabel');
const workspace = document.getElementById('workspace');

const switcherLabel = document.getElementById('switcherLabel');
const scoreChip = document.getElementById('scoreChip');

const problemEmpty = document.getElementById('problemEmpty');
const problemBody = document.getElementById('problemBody');
const problemTitle = document.getElementById('problemTitle');
const problemMeta = document.getElementById('problemMeta');
const problemContent = document.getElementById('problemContent');
const problemRubric = document.getElementById('problemRubric');

const canvasEmpty = document.getElementById('canvasEmpty');
const canvasBody = document.getElementById('canvasBody');
const draftBadge = document.getElementById('draftBadge');
const answerText = document.getElementById('answerText');
const answerHighlight = document.getElementById('answerHighlight');
const wordCounter = document.getElementById('wordCounter');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
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

function enterApp() {
  landingView.hidden = true;
  pageWrap.hidden = false;
  if (currentUser) {
    hideLogin();
  } else {
    showLogin();
  }
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
  showLogin();
}

// ---------- 문제 패널 / 캔버스 표시 ----------
function updateSwitcherLabel() {
  switcherLabel.textContent = selectedProblem
    ? `${selectedProblem.title} — ${formatMeta(selectedProblem.meta)}`
    : '선택된 문제가 없습니다';
}

function renderProblemDrawer() {
  if (!selectedProblem) {
    problemEmpty.hidden = false;
    problemBody.hidden = true;
    return;
  }
  problemEmpty.hidden = true;
  problemBody.hidden = false;
  problemTitle.textContent = selectedProblem.title;
  problemMeta.textContent = `${selectedProblem.source} · ${formatMeta(selectedProblem.meta)}`;
  problemContent.textContent = selectedProblem.content;
  problemRubric.textContent = selectedProblem.rubric || '채점 기준 정보가 없습니다.';
}

function updateCanvasState() {
  if (!selectedProblem) {
    canvasEmpty.hidden = false;
    canvasBody.hidden = true;
    return;
  }
  canvasEmpty.hidden = true;
  canvasBody.hidden = false;
  draftBadge.textContent = hasGradedInSession ? '채점 완료 · 재채점 가능' : '작성 중';
}

function updateScoreChip(result) {
  if (!result) {
    scoreChip.hidden = true;
    return;
  }
  scoreChip.hidden = false;
  document.getElementById('scoreChipNum').textContent = result.score;
  document.getElementById('scoreChipMax').textContent = `/${result.total_max}`;
  document.getElementById('scoreChipTrend').textContent = '';
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
  wordCounter.textContent = `${answerText.value.trim().length}자`;
}

// ---------- 결과 패널 탭 ----------
function setActiveResultTab(tab) {
  document.querySelectorAll('.dtab').forEach((t) => t.classList.toggle('active', t.dataset.tab === tab));
  document.querySelectorAll('.dpanel').forEach((p) => p.classList.toggle('active', p.dataset.panel === tab));
}

function bindTabs() {
  document.querySelectorAll('.dtab').forEach((tab) => {
    tab.addEventListener('click', () => setActiveResultTab(tab.dataset.tab));
  });
}

// ---------- 문제 선택 ----------
function selectProblem(problem) {
  const isDifferentProblem = !selectedProblem || selectedProblem.id !== problem.id;
  selectedProblem = problem;
  currentSession = null;
  resetAnswerPreviewState();
  if (isDifferentProblem) {
    answerText.value = '';
    updateWordCount();
  }
  updateSwitcherLabel();
  renderProblemDrawer();
  resetResultPanels();
  updateCanvasState();
  closeSwitcher();
}

// ---------- 채점 진행 중 로딩 표시 ----------
let gradeLoadingInterval = null;
let gradeLoadingStartTime = null;

function showGradeLoading() {
  document.getElementById('gradeEmpty').hidden = true;
  document.getElementById('gradeContent').hidden = true;
  document.getElementById('gradeLoading').hidden = false;
  gradeLoadingStartTime = Date.now();
  updateGradeLoadingSeconds();
  if (gradeLoadingInterval) clearInterval(gradeLoadingInterval);
  gradeLoadingInterval = setInterval(updateGradeLoadingSeconds, 1000);
}

function updateGradeLoadingSeconds() {
  const el = document.getElementById('gradeLoadingSeconds');
  if (el) el.textContent = Math.floor((Date.now() - gradeLoadingStartTime) / 1000);
}

function hideGradeLoading() {
  if (gradeLoadingInterval) {
    clearInterval(gradeLoadingInterval);
    gradeLoadingInterval = null;
  }
  document.getElementById('gradeLoading').hidden = true;
}

// ---------- 채점 결과 렌더 ----------
function renderScoreResult(result) {
  document.getElementById('gradeEmpty').hidden = true;
  document.getElementById('gradeContent').hidden = false;

  const pct = result.total_max ? Math.round((result.score / result.total_max) * 100) : 0;
  document.getElementById('scoreRing').style.setProperty('--pct', Math.min(100, Math.max(0, pct)));
  document.getElementById('scoreNumber').textContent = result.score;
  document.getElementById('scoreDivider').textContent = `/${result.total_max}`;
  document.getElementById('scoreTitle').textContent = `${selectedProblem?.source || ''} 채점 기준 적용`.trim();
  document.getElementById('scoreSub').textContent = result.commentary || '';

  document.getElementById('criteriaList').innerHTML = (result.scores || [])
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

  document.getElementById('suggestionList').innerHTML =
    (result.suggestions || []).map((s) => `<li>${escapeHtml(s)}</li>`).join('') || '<li>추가 제안이 없습니다.</li>';

  updateScoreChip(result);
}

function formatAttemptDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function renderCompareTable(results) {
  const section = document.getElementById('compareSection');
  const table = document.getElementById('compareTable');
  if (!results || results.length < 2) {
    section.hidden = true;
    table.innerHTML = '';
    return;
  }
  section.hidden = false;

  const latest = results[results.length - 1];
  const labels = (latest.scores || []).map((s) => s.label);
  const headerCells = results
    .map(
      (r, idx) => `
        <th>
          <button type="button" class="compare-attempt-btn" data-attempt-idx="${idx}">
            ${r.attempt}회차<span class="compare-th-date">(${formatAttemptDate(r.created_at)} 작성)</span>
          </button>
        </th>
      `
    )
    .join('');

  let rows = `
    <tr class="compare-total">
      <td>총점</td>
      ${results
        .map((r, idx) => {
          const prev = idx > 0 ? results[idx - 1].score : null;
          const cls = prev === null ? '' : r.score > prev ? 'diff-up' : r.score < prev ? 'diff-down' : '';
          const arrow = prev === null ? '' : r.score > prev ? ' ▲' : r.score < prev ? ' ▼' : '';
          return `<td class="${cls}">${r.score} / ${r.total_max}${arrow}</td>`;
        })
        .join('')}
    </tr>
  `;

  labels.forEach((label) => {
    const cells = results
      .map((r) => {
        const item = (r.scores || []).find((s) => s.label === label);
        return `<td>${item ? `${item.value} / ${item.max_score}` : '—'}</td>`;
      })
      .join('');
    rows += `<tr><td>${escapeHtml(label)}</td>${cells}</tr>`;
  });

  rows += `<tr><td>첨삭 오류 건수</td>${results.map((r) => `<td>${r.grammar_error_count}건</td>`).join('')}</tr>`;

  table.innerHTML = `<thead><tr><th>구분</th>${headerCells}</tr></thead><tbody>${rows}</tbody>`;

  table.querySelectorAll('.compare-attempt-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const idx = Number(btn.dataset.attemptIdx);
      previewAttemptAnswer(results[idx]);
    });
  });
}

// ---------- 채점 비교표 회차 클릭 → 답안 미리보기 ----------
function resetAnswerPreviewState() {
  previewingAttempt = null;
  savedDraftBeforePreview = null;
  answerText.readOnly = false;
  document.getElementById('answerPreviewBanner').hidden = true;
  document.getElementById('btnSubmitAnswer').disabled = false;
  document.getElementById('btnGrade').disabled = false;
}

function previewAttemptAnswer(result) {
  if (result.answer_text === null || result.answer_text === undefined) {
    alert('이 회차는 답안 원문이 저장되기 전이라 불러올 수 없습니다.');
    return;
  }
  if (previewingAttempt === null) {
    savedDraftBeforePreview = answerText.value;
  }
  previewingAttempt = result.attempt;
  answerText.value = result.answer_text;
  answerText.readOnly = true;
  updateWordCount();
  currentErrors = [];
  rebuildHighlight();

  document.getElementById('answerPreviewText').textContent =
    `${result.attempt}회차 (${formatAttemptDate(result.created_at)} 작성) 제출 당시 답안입니다 — 읽기 전용`;
  document.getElementById('answerPreviewBanner').hidden = false;
  document.getElementById('btnSubmitAnswer').disabled = true;
  document.getElementById('btnGrade').disabled = true;
}

function exitAnswerPreview() {
  if (previewingAttempt === null) return;
  answerText.value = savedDraftBeforePreview ?? '';
  updateWordCount();
  currentErrors = [];
  rebuildHighlight();
  resetAnswerPreviewState();
}

async function loadCompareTable() {
  if (!currentSession) return;
  try {
    const results = await fetchApi(`/api/sessions/${currentSession.id}/results`);
    renderCompareTable(results);
  } catch (err) {
    console.error(err);
  }
}

function tagClassForType(type) {
  if (type.includes('비약') || type.includes('논리') || type.includes('단정')) return 'content';
  return 'mech';
}

function renderProofItems(result) {
  const errors = result?.grammar_errors || [];
  currentErrors = errors;
  document.getElementById('proofCount').textContent = errors.length
    ? `감지된 오류 ${errors.length}건 · 어문규정(Bareun) + 첨삭 Agent`
    : '';
  const proofList = document.getElementById('proofList');
  if (!errors.length) {
    proofList.innerHTML = '<div class="proof-card"><span class="proof-tag content">정보</span><div class="proof-note">감지된 첨삭 항목이 없습니다.</div></div>';
    rebuildHighlight();
    return;
  }
  proofList.innerHTML = errors
    .map(
      (item) => `
      <div class="proof-card">
        <span class="proof-tag ${tagClassForType(item.type || '')}">${escapeHtml(item.type || '표현')}</span>
        <div class="proof-diff"><del>${escapeHtml(item.before || '')}</del> → ${escapeHtml(item.after || '')}</div>
        <div class="proof-note">${escapeHtml(item.note || '')}</div>
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
      <div class="chat-msg-row ${message.role === 'assistant' ? '' : 'user'}">
        <div class="chat-avatar">${message.role === 'assistant' ? 'AI' : '나'}</div>
        <div class="chat-bubble">${escapeHtml(message.text)}</div>
      </div>
    `
    )
    .join('');
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

const THINKING_PHRASES = [
  'Tutor가 답변을 생각하고 있어요',
  '채점 결과를 다시 살펴보는 중이에요',
  '질문에 맞는 답을 정리하고 있어요',
  '조금만 더 기다려주세요',
];

let thinkingInterval = null;

function showTypingIndicator() {
  removeTypingIndicator();
  const el = document.createElement('div');
  el.id = 'chatTypingIndicator';
  el.className = 'chat-msg-row typing';
  el.innerHTML = `
    <div class="chat-avatar">AI</div>
    <div class="chat-bubble"><span id="chatTypingText">${escapeHtml(THINKING_PHRASES[0])}</span><span class="typing-dots"><span>.</span><span>.</span><span>.</span></span></div>
  `;
  chatMessages.appendChild(el);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  let idx = 0;
  thinkingInterval = setInterval(() => {
    idx = (idx + 1) % THINKING_PHRASES.length;
    const textEl = document.getElementById('chatTypingText');
    if (textEl) textEl.textContent = THINKING_PHRASES[idx];
  }, 2200);
}

function removeTypingIndicator() {
  if (thinkingInterval) {
    clearInterval(thinkingInterval);
    thinkingInterval = null;
  }
  document.getElementById('chatTypingIndicator')?.remove();
}

function showPostGradeChatHint() {
  const realMessageCount = chatMessages.querySelectorAll('.chat-msg-row').length;
  if (realMessageCount > 1) return;
  renderChatMessages([
    {
      role: 'assistant',
      text:
        '채점이 완료되었습니다! 궁금한 점을 Tutor에게 물어보세요.\n' +
        '예시: "왜 이 점수가 나왔어?" / "첫 번째 첨삭 이유를 자세히 설명해줘" / "어떻게 고치면 점수가 오를까?"',
    },
  ]);
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
    renderSwitcherList();
  } catch (err) {
    console.error(err);
  }
}

// ---------- 문제 전환 오버레이 (검색 + 직접 입력) ----------
function renderSwitcherList() {
  const list = document.getElementById('switcherList');
  if (!problems.length) {
    list.innerHTML = '<div class="panel-empty">등록된 문제가 없습니다.</div>';
    return;
  }
  const groups = [
    { label: '대학 논술', items: problems.filter((p) => p.source === '한양대' || p.source === '경희대') },
    { label: '국립국어원', items: problems.filter((p) => p.source === '국립국어원') },
    { label: '내가 만든 문제', items: problems.filter((p) => p.source === '사용자입력') },
  ].filter((g) => g.items.length);

  list.innerHTML =
    groups
      .map((group) => {
        const rows = group.items
          .map((problem) => {
            const { title, meta } = cardLabel(problem);
            const selected = selectedProblem && selectedProblem.id === problem.id;
            const searchKey = `${title} ${meta}`.toLowerCase();
            return `
              <button type="button" class="switcher-row ${selected ? 'selected' : ''}" data-problem-id="${problem.id}" data-search="${escapeHtml(searchKey)}">
                <div><div class="sr-title">${escapeHtml(title)}</div><div class="sr-meta">${escapeHtml(meta)}</div></div>
                ${selected ? '<svg class="sr-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7" /></svg>' : ''}
              </button>
            `;
          })
          .join('');
        return `<div class="switcher-group-label" data-group>${group.label}</div>${rows}`;
      })
      .join('') +
    `
      <button type="button" class="switcher-new-row" data-search="새 문제 직접 입력">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14" /></svg>
        문제와 채점 기준 직접 입력하기
      </button>
    `;

  list.querySelectorAll('.switcher-row[data-problem-id]').forEach((row) => {
    row.addEventListener('click', () => {
      const id = Number(row.dataset.problemId);
      selectProblem(problems.find((p) => p.id === id));
    });
  });
  list.querySelector('.switcher-new-row')?.addEventListener('click', showCustomForm);
}

function filterSwitcher(query) {
  const q = query.trim().toLowerCase();
  document.querySelectorAll('#switcherList [data-search]').forEach((row) => {
    row.style.display = row.dataset.search.includes(q) ? '' : 'none';
  });
  document.querySelectorAll('#switcherList [data-group]').forEach((label) => {
    let el = label.nextElementSibling;
    let hasVisible = false;
    while (el && !el.hasAttribute('data-group')) {
      if (el.style.display !== 'none') hasVisible = true;
      el = el.nextElementSibling;
    }
    label.style.display = hasVisible ? '' : 'none';
  });
}

function openSwitcher() {
  if (!currentUser) {
    alert('먼저 로그인하세요.');
    return;
  }
  showBrowseMode();
  document.getElementById('switcherOverlay').hidden = false;
  document.getElementById('switcherSearch').focus();
}

function closeSwitcher() {
  document.getElementById('switcherOverlay').hidden = true;
  document.getElementById('switcherSearch').value = '';
  filterSwitcher('');
}

function showBrowseMode() {
  document.getElementById('switcherBrowseHead').hidden = false;
  document.getElementById('switcherList').hidden = false;
  document.getElementById('switcherCustom').hidden = true;
}

function showCustomForm() {
  document.getElementById('switcherBrowseHead').hidden = true;
  document.getElementById('switcherList').hidden = true;
  document.getElementById('switcherCustom').hidden = false;
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

// ---------- 답안 기록 · 채점 비교 통합 슬라이드오버 ----------
function formatHistoryDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

async function openHistoryOverlay() {
  if (!currentUser) {
    alert('먼저 로그인하세요.');
    return;
  }
  const box = document.getElementById('historyList');
  document.getElementById('historyOverlay').hidden = false;
  box.innerHTML = '불러오는 중...';
  try {
    const sessions = await fetchApi(`/api/sessions/user/${currentUser.id}`);
    await renderHistoryList(box, sessions);
  } catch (err) {
    console.error(err);
    box.innerHTML = '<div class="panel-empty">답안 기록을 불러오지 못했습니다. 콘솔을 확인하세요.</div>';
  }
}

function closeHistoryOverlay() {
  document.getElementById('historyOverlay').hidden = true;
}

async function renderHistoryList(box, sessions) {
  if (!sessions.length) {
    box.innerHTML = '<div class="panel-empty">아직 작성한 답안이 없습니다. 문제를 선택해 답안을 작성해보세요.</div>';
    return;
  }

  // 2회 이상 채점된 세션은 회차 비교 요약을 한 줄로 함께 보여준다 (첫 회차 점수 조회 필요).
  const multi = sessions.filter((s) => s.attempt_count >= 2);
  const resultsBySession = {};
  await Promise.all(
    multi.map(async (s) => {
      try {
        resultsBySession[s.id] = await fetchApi(`/api/sessions/${s.id}/results`);
      } catch (err) {
        console.error(err);
      }
    })
  );

  box.innerHTML = sessions
    .map((s) => {
      const scoreLabel = s.latest_score === null || s.latest_score === undefined
        ? '<span class="he-score pending">미채점</span>'
        : `<span class="he-score">${s.latest_score} / ${s.latest_total_max}</span>`;
      const results = resultsBySession[s.id];
      let compareLine = '';
      if (results && results.length >= 2) {
        const first = results[0];
        const last = results[results.length - 1];
        const arrow = last.score > first.score ? '▲' : last.score < first.score ? '▼' : '';
        compareLine = `<div class="he-compare">${first.attempt}회차 ${first.score}/${first.total_max} → <b>${last.attempt}회차 ${last.score}/${last.total_max} ${arrow}${Math.abs(last.score - first.score) || ''}</b></div>`;
      }
      return `
        <button type="button" class="history-entry" data-session-id="${s.id}">
          <div class="he-top">
            <div><div class="he-title">${escapeHtml(s.problem_title)}</div><div class="he-meta">${escapeHtml(s.problem_source)} · ${formatHistoryDate(s.created_at)}</div></div>
            ${scoreLabel}
          </div>
          ${compareLine}
        </button>
      `;
    })
    .join('');

  box.querySelectorAll('.history-entry').forEach((entry) => {
    entry.addEventListener('click', () => resumeSession(Number(entry.dataset.sessionId)));
  });
}

async function resumeSession(sessionId) {
  try {
    const session = await fetchApi(`/api/sessions/${sessionId}`);
    let problem = problems.find((p) => p.id === session.problem_id);
    if (!problem && session.problem_id) {
      problem = await fetchApi(`/api/problems/${session.problem_id}`);
    }
    if (!problem) {
      alert('이 답안이 연결된 문제 정보를 찾을 수 없습니다.');
      return;
    }

    const [answer, results] = await Promise.all([
      fetchApi(`/api/sessions/${session.id}/answer`),
      fetchApi(`/api/sessions/${session.id}/results`),
    ]);

    selectedProblem = problem;
    currentSession = session;
    resetAnswerPreviewState();
    updateSwitcherLabel();
    renderProblemDrawer();

    answerText.value = answer ? answer.text : '';
    updateWordCount();
    currentErrors = [];

    hasGradedInSession = results.length > 0;
    if (hasGradedInSession) {
      const latest = results[results.length - 1];
      renderScoreResult(latest);
      renderProofItems(latest);
      renderCompareTable(results);
      showPostGradeChatHint();
    } else {
      document.getElementById('gradeEmpty').hidden = false;
      document.getElementById('gradeContent').hidden = true;
      document.getElementById('compareSection').hidden = true;
      document.getElementById('compareTable').innerHTML = '';
      renderProofItems(null);
      updateScoreChip(null);
      renderChatMessages([
        { role: 'assistant', text: '세션을 시작하고 채점을 완료하면 Tutor에게 채점 결과에 대해 질문할 수 있습니다.' },
      ]);
    }
    updateCanvasState();
    setActiveResultTab('grade');
    closeHistoryOverlay();
    closeSwitcher();
  } catch (err) {
    console.error(err);
    alert('답안 기록을 불러오는 데 실패했습니다. 콘솔을 확인하세요.');
  }
}

function resetResultPanels() {
  hasGradedInSession = false;
  document.getElementById('gradeEmpty').hidden = false;
  document.getElementById('gradeContent').hidden = true;
  document.getElementById('compareSection').hidden = true;
  document.getElementById('compareTable').innerHTML = '';
  currentErrors = [];
  rebuildHighlight();
  document.getElementById('proofCount').textContent = '';
  document.getElementById('proofList').innerHTML =
    '<div class="proof-card"><span class="proof-tag content">정보</span><div class="proof-note">채점 후 문법 및 첨삭 항목이 표시됩니다.</div></div>';
  updateScoreChip(null);
  renderChatMessages([
    { role: 'assistant', text: '세션을 시작하고 채점을 완료하면 Tutor에게 채점 결과에 대해 질문할 수 있습니다.' },
  ]);
  setActiveResultTab('grade');
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
    resetResultPanels();
  } catch (err) {
    console.error(err);
    alert('세션 생성에 실패했습니다. 콘솔을 확인하세요.');
  }
}

let sessionAutoStartInFlight = false;

async function ensureSessionStarted() {
  if (currentSession || sessionAutoStartInFlight) return;
  if (!currentUser || !selectedProblem) return;
  sessionAutoStartInFlight = true;
  try {
    await createSession();
  } finally {
    sessionAutoStartInFlight = false;
  }
}

let saveStatusTimer = null;

function showSaveStatus(message) {
  const el = document.getElementById('answerSaveStatus');
  if (!el) return;
  el.textContent = message;
  if (saveStatusTimer) clearTimeout(saveStatusTimer);
  saveStatusTimer = setTimeout(() => {
    el.textContent = '';
  }, 2500);
}

// 저장 성공 시 true, 실패(세션 없음/빈 답안/네트워크 오류) 시 false를 반환한다.
// gradeAnswer()가 이 값을 보고 채점 진행 여부를 판단하므로, 실패를 삼키지 말고 반드시 알려야 한다.
async function saveAnswer() {
  if (!currentSession) {
    alert('세션을 먼저 시작하세요.');
    return false;
  }
  const text = answerText.value.trim();
  if (!text) {
    alert('답안을 입력하세요.');
    return false;
  }
  try {
    await fetchApi('/api/answers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: currentSession.id, text, status: 'draft' }),
    });
    showSaveStatus('답안이 저장되었습니다.');
    return true;
  } catch (err) {
    console.error(err);
    alert('답안 저장에 실패했습니다. 콘솔을 확인하세요.');
    return false;
  }
}

async function gradeAnswer() {
  if (!currentSession) {
    alert('세션을 먼저 시작하고 답안을 저장하세요.');
    return;
  }
  // 채점 전 항상 현재 답안을 먼저 저장한다. 저장이 실패하면(빈 답안, 네트워크 오류 등)
  // saveAnswer()가 이미 사용자에게 알렸으므로 여기서는 조용히 채점을 중단한다 —
  // 그렇지 않으면 화면의 최신 텍스트와 실제로 채점되는 답안이 어긋날 수 있다.
  const saved = await saveAnswer();
  if (!saved) return;

  const btnGrade = document.getElementById('btnGrade');
  const hadPriorResult = hasGradedInSession;
  btnGrade.disabled = true;
  btnGrade.textContent = '채점 중...';
  isGrading = true;
  setActiveResultTab('grade');
  document.getElementById('workspace').classList.remove('drawer-collapsed');
  showGradeLoading();
  try {
    const result = await fetchApi('/api/grade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: currentSession.id, source: 'ui' }),
    });
    hasGradedInSession = true;
    isGrading = false;
    updateCanvasState();
    hideGradeLoading();
    renderScoreResult(result);
    renderProofItems(result);
    showPostGradeChatHint();
    await loadCompareTable();
  } catch (err) {
    console.error(err);
    alert('채점에 실패했습니다. 콘솔을 확인하세요.');
    isGrading = false;
    updateCanvasState();
    hideGradeLoading();
    document.getElementById('gradeContent').hidden = !hadPriorResult;
    document.getElementById('gradeEmpty').hidden = hadPriorResult;
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

  const existing = [...chatMessages.querySelectorAll('.chat-msg-row')].map((node) => ({
    role: node.classList.contains('user') ? 'user' : 'assistant',
    text: node.querySelector('.chat-bubble')?.textContent || '',
  }));
  existing.push({ role: 'user', text });
  renderChatMessages(existing);
  showTypingIndicator();

  const btnSend = document.getElementById('btnSendChat');
  btnSend.disabled = true;
  try {
    const response = await fetchApi('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: currentSession.id, text }),
    });
    removeTypingIndicator();
    renderChatMessages(response.messages);
  } catch (err) {
    console.error(err);
    removeTypingIndicator();
    alert('Tutor 응답을 받는 데 실패했습니다. 콘솔을 확인하세요.');
  } finally {
    btnSend.disabled = false;
  }
}

// ---------- 이벤트 바인딩 ----------
function bindEvents() {
  document.getElementById('btnLandingStart').onclick = enterApp;
  document.getElementById('btnLogin').onclick = doLogin;
  document.getElementById('loginInput').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') doLogin();
  });
  document.getElementById('btnSwitchUser').onclick = switchUser;

  document.getElementById('btnSubmitAnswer').onclick = saveAnswer;
  document.getElementById('btnGrade').onclick = gradeAnswer;
  document.getElementById('btnExitPreview').onclick = exitAnswerPreview;
  answerText.addEventListener('input', () => {
    updateWordCount();
    currentErrors = [];
    rebuildHighlight();
    ensureSessionStarted();
  });
  answerText.addEventListener('scroll', syncHighlightScroll);

  document.getElementById('btnSendChat').onclick = sendChat;
  chatInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') sendChat();
  });

  // 문제 전환 오버레이
  document.getElementById('btnSwitcher').onclick = openSwitcher;
  document.getElementById('btnCloseSwitcher').onclick = closeSwitcher;
  document.getElementById('btnCloseSwitcher2').onclick = closeSwitcher;
  document.getElementById('switcherOverlay').addEventListener('click', (e) => {
    if (e.target.id === 'switcherOverlay') closeSwitcher();
  });
  document.getElementById('switcherSearch').addEventListener('input', (e) => filterSwitcher(e.target.value));
  document.getElementById('btnBackToBrowse').onclick = showBrowseMode;
  document.getElementById('btnGenerateRubric').onclick = generateRubric;
  document.getElementById('btnCreateProblem').onclick = createCustomProblem;

  // 답안 기록 · 채점 비교 슬라이드오버
  document.getElementById('btnHistory').onclick = openHistoryOverlay;
  document.getElementById('btnCloseHistory').onclick = closeHistoryOverlay;
  document.getElementById('historyOverlay').addEventListener('click', (e) => {
    if (e.target.id === 'historyOverlay') closeHistoryOverlay();
  });

  // 좌우 드로어 접기/펼치기
  document.getElementById('btnProblemDrawerToggle').onclick = () => {
    workspace.classList.toggle('problem-collapsed');
  };
  document.getElementById('btnDrawerToggle').onclick = () => {
    workspace.classList.toggle('drawer-collapsed');
  };

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    closeSwitcher();
    closeHistoryOverlay();
  });

  bindTabs();
}

async function healthCheck() {
  try {
    await fetch(`${API}/health`);
  } catch (err) {
    console.error('Backend not ready yet', err);
  }
}

async function init() {
  bindEvents();
  const storedUser = loadStoredUser();
  if (storedUser) {
    currentUser = storedUser;
    userLabel.textContent = storedUser.identifier;
  }
  await loadProblems();
  updateSwitcherLabel();
  renderProblemDrawer();
  updateCanvasState();
  updateWordCount();
  rebuildHighlight();
  healthCheck();
}

init();
