// 프론트엔드 브라우저 스모크 테스트 (Playwright).
// 사전 준비: backend(uvicorn, :8000)와 `npm run dev`(:5173)가 떠 있어야 함.
//   npm install --no-save playwright && npx playwright install chromium && node smoke.mjs
import { chromium } from 'playwright'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } })

const errors = []
page.on('console', (msg) => {
  if (msg.type() === 'error') errors.push(msg.text())
})
page.on('pageerror', (err) => errors.push(String(err)))

const uniqueUser = `smoke-${Date.now()}`

try {
  await page.goto('http://localhost:5173/')
  await page.waitForSelector('select')
  await page.waitForFunction(() => document.querySelector('select')?.options.length > 1)
  await page.fill('.user-field input', uniqueUser)
  await page.screenshot({ path: 'screenshots/01-loaded.png', fullPage: true })

  // 문제 선택 + 1차 채점
  await page.selectOption('select', { index: 1 })
  await page.waitForSelector('.problem-content')
  await page.fill('.answer-input', '로봇세는 필요하다. 왜냐하면 필요하기 때문이다.')
  await page.click('button:has-text("채점 요청")')
  await page.waitForSelector('.score-badge-value', { timeout: 90000 })
  await page.screenshot({ path: 'screenshots/02-graded-round1.png', fullPage: true })

  // 첨삭 목록 탭
  await page.click('.tab-bar button:has-text("첨삭 목록")')
  await page.click('button:has-text("문법/표현 첨삭")')
  await page.waitForSelector('.tab-content li', { timeout: 90000 })
  await page.screenshot({ path: 'screenshots/03-feedback-tab.png', fullPage: true })

  // Tutor Chat 탭 - WS 연결 확인
  await page.click('.tab-bar button:has-text("Tutor Chat")')
  await page.waitForSelector('.chat-status-open', { timeout: 15000 })
  await page.screenshot({ path: 'screenshots/04-chat-tab.png', fullPage: true })

  // 2차 재채점 (같은 세션) - 비교표 재료 만들기
  await page.click('.tab-bar button:has-text("채점 결과")')
  await page.fill(
    '.answer-input',
    '로봇세는 도입해야 한다. 일자리를 잃는 노동자를 지원할 재원이 필요하기 때문이다. 다만 세율은 낮게 시작해 점진적으로 조정해야 한다.',
  )
  await page.click('button:has-text("재채점")')
  await page.waitForFunction(
    () => document.querySelector('.score-badge-meta strong')?.textContent.includes('2차'),
    undefined,
    { timeout: 90000 },
  )
  await page.screenshot({ path: 'screenshots/05-graded-round2.png', fullPage: true })

  // 지난 세션 화면
  await page.click('button:has-text("지난 세션")')
  await page.waitForSelector('.session-list-item')
  await page.screenshot({ path: 'screenshots/06-history-list.png', fullPage: true })

  await page.click('.session-list-item')
  await page.waitForSelector('.comparison-table')
  await page.screenshot({ path: 'screenshots/07-history-detail.png', fullPage: true })

  console.log('CONSOLE_ERRORS:', JSON.stringify(errors))
} finally {
  // WS 연결이 열린 채로 남아 서버 쪽에 좀비 커넥션(및 SQLite 세션)이 남지 않도록
  // 실패하더라도 항상 브라우저를 정리한다.
  await browser.close()
}
