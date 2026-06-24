import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// mock 掉 API 层，只测 store 自身的状态流转逻辑
vi.mock('@/api/index', () => ({
  checkHealth: vi.fn(),
  getDataStats: vi.fn(),
}))

import { checkHealth, getDataStats } from '@/api/index'
import { useAppStore } from '@/stores/app'

describe('useAppStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('checkBackend 成功时置 backendOnline=true', async () => {
    vi.mocked(checkHealth).mockResolvedValue({} as never)
    const store = useAppStore()

    await store.checkBackend()

    expect(store.backendOnline).toBe(true)
  })

  it('checkBackend 失败时置 backendOnline=false（吞掉异常）', async () => {
    vi.mocked(checkHealth).mockRejectedValue(new Error('connection refused'))
    const store = useAppStore()
    store.backendOnline = true // 先置真，验证会被改回 false

    await store.checkBackend()

    expect(store.backendOnline).toBe(false)
  })

  it('fetchStats 成功时写入返回的统计数据', async () => {
    const stats = {
      stock_count: 5000,
      quote_count: 22_000_000,
      financial_count: 100,
      latest_trade_date: '20260624',
      strategy_count: 3,
    }
    vi.mocked(getDataStats).mockResolvedValue({ data: stats } as never)
    const store = useAppStore()

    await store.fetchStats()

    expect(store.stats).toEqual(stats)
  })

  it('fetchStats 失败时静默保持原值', async () => {
    vi.mocked(getDataStats).mockRejectedValue(new Error('500'))
    const store = useAppStore()
    const before = { ...store.stats }

    await store.fetchStats()

    expect(store.stats).toEqual(before)
  })
})
