// 3단 레이아웃 + 채점기준 접기/펼치기 검증용 Playwright 스크립트.
// 사전 준비: backend(:8000), `npm run dev`(:5173)가 떠 있어야 함.
import { chromium } from 'playwright'

const browser = await chromium.launch()
const errors = []

try {
  // ---------- 데스크톱: 3단 가로 배치 확인 ----------
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  page.on('console', (msg) => msg.type() === 'error' && errors.push(msg.text()))
  page.on('pageerror', (err) => errors.push(String(err)))

  await page.goto('http://localhost:5173/')
  await page.waitForSelector('select')
  await page.waitForFunction(() => document.querySelector('select')?.options.length > 1)
  await page.selectOption('select', { index: 1 })
  await page.waitForSelector('.problem-content')

  const problemBox = await page.locator('.problem-panel').boundingBox()
  const answerBox = await page.locator('.answer-panel').boundingBox()
  const resultBox = await page.locator('.result-panel-outer').boundingBox()
  console.log('데스크톱 패널 x좌표:', {
    problem: problemBox.x,
    answer: answerBox.x,
    result: resultBox.x,
  })
  const sameRow = Math.abs(problemBox.y - answerBox.y) < 5 && Math.abs(answerBox.y - resultBox.y) < 5
  const leftToRight = problemBox.x < answerBox.x && answerBox.x < resultBox.x
  console.log('3단 가로 배치 여부:', sameRow && leftToRight)
  if (!(sameRow && leftToRight)) throw new Error('데스크톱에서 3단이 가로로 나란히 배치되지 않음')

  // 채점 기준 기본 접힘 확인
  const rubricVisibleBefore = await page.locator('.rubric-editor').count()
  console.log('토글 전 rubric-editor 노출 개수 (0이어야 함):', rubricVisibleBefore)
  if (rubricVisibleBefore !== 0) throw new Error('채점 기준이 기본적으로 펼쳐져 있음 (접힘 상태여야 함)')

  await page.screenshot({ path: 'screenshots/layout-01-desktop-collapsed.png', fullPage: true })

  // 채점 기준 펼치기
  await page.click('button:has-text("채점 기준 보기")')
  await page.waitForSelector('.rubric-editor')
  console.log('토글 후 rubric-editor 노출:', await page.locator('.rubric-editor').isVisible())
  await page.screenshot({ path: 'screenshots/layout-02-desktop-rubric-open.png', fullPage: true })

  // 다시 접기
  await page.click('button:has-text("채점 기준 보기")')
  await page.waitForFunction(() => document.querySelectorAll('.rubric-editor').length === 0)
  console.log('재클릭 후 다시 접힘 확인 완료')

  // 문항 텍스트가 길 때 내부 스크롤 영역이 실제로 스크롤 가능한지 (scrollHeight > clientHeight)
  const scrollable = await page.locator('.problem-scroll-area').evaluate((el) => el.scrollHeight > el.clientHeight)
  console.log('문항 영역 내부 스크롤 가능 여부:', scrollable)

  await page.close()

  // ---------- 모바일 폭: 세로 스택 확인 ----------
  const mobilePage = await browser.newPage({ viewport: { width: 480, height: 900 } })
  mobilePage.on('console', (msg) => msg.type() === 'error' && errors.push(msg.text()))
  mobilePage.on('pageerror', (err) => errors.push(String(err)))

  await mobilePage.goto('http://localhost:5173/')
  await mobilePage.waitForSelector('select')
  await mobilePage.waitForFunction(() => document.querySelector('select')?.options.length > 1)
  await mobilePage.selectOption('select', { index: 1 })
  await mobilePage.waitForSelector('.problem-content')

  const mProblem = await mobilePage.locator('.problem-panel').boundingBox()
  const mAnswer = await mobilePage.locator('.answer-panel').boundingBox()
  const mResult = await mobilePage.locator('.result-panel-outer').boundingBox()
  console.log('모바일 패널 y좌표:', { problem: mProblem.y, answer: mAnswer.y, result: mResult.y })
  const stacked = mAnswer.y >= mProblem.y + mProblem.height - 5 && mResult.y >= mAnswer.y + mAnswer.height - 5
  console.log('모바일에서 세로 스택 여부:', stacked)
  if (!stacked) throw new Error('좁은 화면에서 세로로 쌓이지 않음')

  await mobilePage.screenshot({ path: 'screenshots/layout-03-mobile-stacked.png', fullPage: true })
  await mobilePage.close()

  console.log('CONSOLE_ERRORS:', JSON.stringify(errors))
  console.log('\n모든 레이아웃 검증 통과.')
} finally {
  await browser.close()
}