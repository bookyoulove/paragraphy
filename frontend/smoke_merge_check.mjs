// App.jsx 머지 컨플릭트 해소 후, 화면이 정상적으로 뜨는지 확인하는 스크립트.
import { chromium } from 'playwright'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
const errors = []
page.on('console', (msg) => msg.type() === 'error' && errors.push(msg.text()))
page.on('pageerror', (err) => errors.push(String(err)))

try {
  await page.goto('http://localhost:5173/')
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: 'screenshots/merge-01-root.png', fullPage: true })

  const bodyText = await page.locator('body').innerText()
  console.log('body 텍스트 길이:', bodyText.length)
  console.log('body 미리보기:', bodyText.slice(0, 200))

  // 라우팅 확인: /problems 로 직접 이동해봤을 때 예외 없이 렌더되는지
  await page.goto('http://localhost:5173/problems')
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: 'screenshots/merge-02-problems-route.png', fullPage: true })

  console.log('CONSOLE_ERRORS:', JSON.stringify(errors))
  if (errors.length > 0) {
    console.log('\n콘솔 에러가 있습니다 (위 참고).')
  } else {
    console.log('\n콘솔 에러 없음.')
  }
} finally {
  await browser.close()
}