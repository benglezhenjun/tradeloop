import { test, expect } from '@playwright/test'

// 烟测：不求覆盖业务，只确认「应用真的跑起来、关键页面打得开、不白屏/不抛异常」——
// 这是单测覆盖不到的：构建产物 + 路由 + 组件挂载在真实浏览器里是否成立。

test('应用外壳渲染：品牌与导航可见，无未捕获异常/未解析组件', async ({ page }) => {
  const pageErrors: Error[] = []
  const unresolvedComponents: string[] = []
  page.on('pageerror', (err) => pageErrors.push(err))
  page.on('console', (msg) => {
    if (msg.text().includes('Failed to resolve component')) unresolvedComponents.push(msg.text())
  })

  await page.goto('/')

  await expect(page.getByText('TradeLoop')).toBeVisible()
  await expect(page.getByRole('menuitem', { name: '仪表盘' })).toBeVisible()
  await expect(page.getByRole('menuitem', { name: '设置' })).toBeVisible()

  expect(pageErrors, `未捕获异常：${pageErrors.map((e) => e.message).join('; ')}`).toHaveLength(0)
  expect(unresolvedComponents, `未注册组件：${unresolvedComponents.join('; ')}`).toHaveLength(0)
})

test('客户端路由：切到设置页不白屏', async ({ page }) => {
  await page.goto('/')

  await page.getByRole('menuitem', { name: '设置' }).click()

  await expect(page).toHaveURL(/\/settings$/)
  await expect(page.getByText('设置与数据管理')).toBeVisible()
})

test('客户端路由：策略管理页可达', async ({ page }) => {
  await page.goto('/strategies')
  // 路由命中且页面有内容（不抛异常、非空白）
  await expect(page.locator('.el-main')).toBeVisible()
  await expect(page.getByRole('menuitem', { name: '策略管理' })).toBeVisible()
})
