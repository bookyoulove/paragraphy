import { chromium } from 'playwright'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
const errors = []
page.on('console', (msg) => msg.type() === 'error' && errors.push(msg.text()))
page.on('pageerror', (err) => errors.push(String(err)))

try {
  await page.goto('http://localhost:5173/problems')
  await page.waitForSelector('input[placeholder="예: yujin"]')
  await page.fill('input[placeholder="예: yujin"]', `merge-check-${Date.now()}`)
  await page.fill('input[type="password"], input[placeholder="비밀번호 입력"]', 'anything')
  await page.click('button:has-text("시작하기")')

  await page.waitForSelector('.tutor-chat-fab, text=문제 선택', { timeout: 15000 }).catch(() => {})
  await page.waitForTimeout(2000)
  await page.screenshot({ path: 'screenshots/merge-03-logged-in-problems.png', fullPage: true })

  const bodyText = await page.locator('body').innerText()
  console.log('로그인 후 body 텍스트 길이:', bodyText.length)
  console.log('CONSOLE_ERRORS:', JSON.stringify(errors))
} finally {
  await browser.close()
}