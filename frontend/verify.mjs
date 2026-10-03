/**
 * 浏览器端真实验证
 * ------------------------------------------------------------
 * 编译通过 ≠ 界面能用。这个脚本真的开一个浏览器，
 * 走一遍登录 → 上传 → 检索 → 问答，并截图。
 */
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:5173'
const SHOTS = 'shots'
fs.mkdirSync(SHOTS, { recursive: true })

const errors = []
const results = []

function log(ok, msg) {
  results.push({ ok, msg })
  console.log(`${ok ? '✓' : '✗'} ${msg}`)
}

// 用 channel: 'chromium' 走已下载的完整 chromium，
// 避开单独的 chrome-headless-shell（那是另一个 400MB 下载）
const browser = await chromium.launch({ channel: 'chromium' })
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } })

// 收集浏览器控制台错误和失败的请求 —— 这是"白屏"类问题的主要来源
page.on('console', (m) => {
  if (m.type() === 'error') errors.push(`console: ${m.text()}`)
})
page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))
page.on('requestfailed', (r) => {
  errors.push(`requestfailed: ${r.url()} - ${r.failure()?.errorText}`)
})

try {
  // ---------- 1. 登录页 ----------
  await page.goto(BASE + '/login', { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  const hasBrand = await page.locator('.auth-head h1').textContent()
  log(hasBrand.includes('Knowledge Agent'), `登录页渲染: "${hasBrand}"`)
  await page.screenshot({ path: `${SHOTS}/01-login.png` })

  // ---------- 2. 登录 ----------
  await page.fill('input[autocomplete="username"]', 'lisi')
  await page.fill('input[type="password"]', '123456')
  await page.click('button[type="submit"]')
  await page.waitForURL('**/chat', { timeout: 20000 })
  await page.waitForTimeout(900)
  log(true, '登录成功并跳转到 /chat')
  await page.screenshot({ path: `${SHOTS}/02-chat-empty.png` })

  // ---------- 3. 对话（真实 RAG 调用） ----------
  await page.fill('.composer-input', '出差住宿标准是多少钱？')
  await page.click('.send-btn')
  await page.waitForSelector('.sources', { timeout: 90000 })
  await page.waitForTimeout(500)
  const answer = await page.locator('.answer-text').last().textContent()
  const nSources = await page.locator('.source-card').count()
  log(answer.length > 10, `RAG 回答长度 ${answer.length} 字, ${nSources} 条来源`)
  await page.screenshot({ path: `${SHOTS}/03-chat-answer.png` })

  // ---------- 4. 拒答场景 ----------
  await page.fill('.composer-input', '推荐一部好看的电影')
  await page.click('.send-btn')
  await page.waitForTimeout(9000)
  const answers = await page.locator('.answer-text').allTextContents()
  const last = answers[answers.length - 1] || ''
  log(last.includes('没有'), `无答案时正确拒答: "${last.slice(0, 30)}"`)
  await page.screenshot({ path: `${SHOTS}/04-chat-refuse.png` })

  // ---------- 5. 检索页 ----------
  await page.click('a[href="/search"]')
  await page.waitForTimeout(500)
  await page.fill('.search-input', '年假')
  await page.locator('.search-bar button').click()
  await page.waitForTimeout(8000)
  const hits = await page.locator('.hit-card').count()
  log(true, `检索页返回 ${hits} 条结果`)
  if (hits > 0) {
    const scoreTxt = await page.locator('.score-num').first().textContent()
    log(/^0\.\d+$/.test(scoreTxt), `相似度显示: ${scoreTxt}`)
  }
  await page.screenshot({ path: `${SHOTS}/05-search.png` })

  // ---------- 6. 检索空结果 ----------
  await page.fill('.search-input', '如何用Python写爬虫')
  await page.locator('.search-bar button').click()
  await page.waitForTimeout(8000)
  const emptyShown = await page.locator('.empty-result').count()
  log(emptyShown > 0, '无结果时显示了解释性空状态')
  await page.screenshot({ path: `${SHOTS}/06-search-empty.png` })

  // ---------- 7. 文档页 ----------
  await page.click('a[href="/documents"]')
  await page.waitForTimeout(1200)
  const rows = await page.locator('.doc-row:not(.doc-head)').count()
  log(rows > 0, `文档列表显示 ${rows} 篇`)
  const stats = await page.locator('.stat-value').allTextContents()
  log(true, `统计卡片: ${stats.join(' / ')}`)
  await page.screenshot({ path: `${SHOTS}/07-documents.png` })

  // ---------- 8. 上传 ----------
  // 用相对路径 —— /tmp 在 Windows 上不存在（会落到 D:\tmp）
  const uploadPath = 'upload_test.txt'
  fs.writeFileSync(uploadPath, '本文件由自动化测试创建。\n\n测试要点：上传、切块、向量化、列表刷新。\n\n公司的年会定于每年一月举行。\n')
  await page.setInputFiles('input[type="file"]', uploadPath)
  await page.waitForTimeout(12000)
  const rows2 = await page.locator('.doc-row:not(.doc-head)').count()
  log(rows2 > rows, `上传后文档数 ${rows} → ${rows2}`)
  await page.screenshot({ path: `${SHOTS}/08-uploaded.png` })

  // ---------- 9. 删除弹窗 ----------
  await page.locator('.doc-row:not(.doc-head)').first().locator('button').click()
  await page.waitForTimeout(500)
  const modal = await page.locator('.modal').count()
  log(modal > 0, '删除确认弹窗出现')
  await page.screenshot({ path: `${SHOTS}/09-delete-modal.png` })

  // 真的删掉它，顺便验证删除链路
  await page.click('.modal .btn-danger')
  await page.waitForTimeout(8000)
  const rows3 = await page.locator('.doc-row:not(.doc-head)').count()
  log(rows3 < rows2, `删除后文档数 ${rows2} → ${rows3}`)
  await page.screenshot({ path: `${SHOTS}/10-after-delete.png` })

  // ---------- 10. 窄屏 ----------
  await page.setViewportSize({ width: 420, height: 860 })
  await page.goto(BASE + '/chat', { waitUntil: 'networkidle' })
  await page.waitForTimeout(800)
  await page.screenshot({ path: `${SHOTS}/11-mobile.png` })
  log(true, '窄屏截图已保存')

} catch (e) {
  log(false, `异常: ${e.message}`)
  await page.screenshot({ path: `${SHOTS}/error.png` }).catch(() => {})
} finally {
  console.log('\n========================================')
  const failed = results.filter((r) => !r.ok)
  console.log(`通过 ${results.length - failed.length}/${results.length}`)
  if (errors.length) {
    console.log('\n浏览器错误:')
    errors.slice(0, 15).forEach((e) => console.log('  ! ' + e))
  } else {
    console.log('无浏览器控制台错误')
  }
  await browser.close()
}
