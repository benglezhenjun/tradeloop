import { defineConfig, devices } from '@playwright/test'

// E2E 烟测：验证前端外壳能真正渲染、客户端路由可用、无未捕获异常。
// 只测前端（不依赖后端——应用在后端离线时也应优雅降级显示空态）。
// 测试放在 e2e/，与 src/ 下的 vitest 单测互不干扰。
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
