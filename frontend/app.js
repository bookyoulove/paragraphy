const API = 'http://127.0.0.1:8000';

const scoreData = {
  summary: { score: 73, total: 100, title: '국립국어원 채점 기준 적용', note: '논리적 비약이 감지 요인이며, 표현력은 양호한 수준입니다.' },
  criteria: [
    { label: '내용 (기준 충족도)', value: 16, total: 20 },
    { label: '조직 (논리적 구성)', value: 14, total: 20 },
    { label: '표현 (문장력)', value: 15, total: 20 },
    { label: '논리성 (논증 타당성)', value: 13, total: 20 },
    { label: '완성도 (전체 관찰)', value: 15, total: 20 }
  ]
};

function renderScorePanels() {
  const rings = document.querySelectorAll('.score-ring');
  rings.forEach((ring) => {
    ring.style.setProperty('--score', 73);
  });

  const criterionNodes = document.querySelectorAll('.criteria-item');
  scoreData.criteria.forEach((item, idx) => {
    if (!criterionNodes[idx]) return;
    const ratio = (item.value / item.total) * 100;
    const bar = criterionNodes[idx].querySelector('.bar span');
    if (bar) bar.style.width = `${ratio}%`;
    criterionNodes[idx].querySelector('.criteria-row span:last-child').textContent = `${item.value} / ${item.total}`;
  });
}

function renderTutorChat() {
  const chatBox = document.querySelector('.chat-panel');
  if (!chatBox) return;
  const userMsg = `채점 점수가 낮은 이유를 설명해줘.`;
  const assistantMsg = `논리적 비약이 보이고, 제시문 (다)와 연결되는 근거가 다소 약합니다. 첫 문단에서 공통 핵심을 정리한 뒤, 결론을 뚜렷하게 제시하면 점수가 올라갑니다.`;
  chatBox.innerHTML = `
    <div class="chat-box chat-user">
      <div class="chat-badge">교사</div>
      <div class="chat-msg">${userMsg}</div>
    </div>
    <div class="chat-box chat-assistant">
      <div class="chat-badge assistant">AI</div>
      <div class="chat-msg">${assistantMsg}</div>
    </div>
    <div class="chat-input-wrap">
      <input type="text" placeholder="Tutor에게 질문하기" />
      <button class="primary-btn small-btn">전송</button>
    </div>
  `;
}

async function healthCheck() {
  try {
    const res = await fetch(`${API}/health`);
    const data = await res.json();
    const status = document.querySelector('.topbar-meta');
    if (status) status.textContent = `대입 논술 채점 · 첨삭 · ${data.environment || 'online'}`;
  } catch (err) {
    console.log('Backend not ready yet', err);
  }
}

renderScorePanels();
renderTutorChat();
healthCheck();
