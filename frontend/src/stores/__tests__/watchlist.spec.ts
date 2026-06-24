import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/api/index', () => ({
  listWatchlistGroups: vi.fn(),
  getGroupStocks: vi.fn(),
  getAllWatchlistStocks: vi.fn(),
  createWatchlistGroup: vi.fn(),
  deleteWatchlistGroup: vi.fn(),
  addStockToGroup: vi.fn(),
  removeStockFromGroup: vi.fn(),
  batchAddStocks: vi.fn(),
}))

import {
  createWatchlistGroup,
  getAllWatchlistStocks,
  getGroupStocks,
  listWatchlistGroups,
} from '@/api/index'
import { useWatchlistStore } from '@/stores/watchlist'

describe('useWatchlistStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchGroups 从 res.data.items 写入分组', async () => {
    const groups = [{ id: 1, name: '核心池', description: '', stock_count: 0 }]
    vi.mocked(listWatchlistGroups).mockResolvedValue({ data: { items: groups, total: 1 } } as never)
    const store = useWatchlistStore()

    await store.fetchGroups()

    expect(store.groups).toEqual(groups)
  })

  it('fetchStocks 传 groupId 时走分组端点', async () => {
    vi.mocked(getGroupStocks).mockResolvedValue({ data: { items: [{ ts_code: '600000.SH' }], total: 1 } } as never)
    const store = useWatchlistStore()

    await store.fetchStocks(7)

    expect(getGroupStocks).toHaveBeenCalledWith(7)
    expect(getAllWatchlistStocks).not.toHaveBeenCalled()
    expect(store.stocks).toHaveLength(1)
  })

  it('fetchStocks 不传 groupId 时走全量端点', async () => {
    vi.mocked(getAllWatchlistStocks).mockResolvedValue({ data: { items: [], total: 0 } } as never)
    const store = useWatchlistStore()

    await store.fetchStocks(null)

    expect(getAllWatchlistStocks).toHaveBeenCalled()
    expect(getGroupStocks).not.toHaveBeenCalled()
  })

  it('fetchStocks 结束后 loading 复位为 false', async () => {
    vi.mocked(getAllWatchlistStocks).mockResolvedValue({ data: { items: [], total: 0 } } as never)
    const store = useWatchlistStore()

    await store.fetchStocks(null)

    expect(store.loading).toBe(false)
  })

  it('addGroup 成功返回 true 并触发刷新', async () => {
    vi.mocked(createWatchlistGroup).mockResolvedValue({} as never)
    vi.mocked(listWatchlistGroups).mockResolvedValue({ data: { items: [], total: 0 } } as never)
    vi.mocked(getAllWatchlistStocks).mockResolvedValue({ data: { items: [], total: 0 } } as never)
    const store = useWatchlistStore()

    const ok = await store.addGroup('新分组', '描述')

    expect(ok).toBe(true)
    expect(createWatchlistGroup).toHaveBeenCalledWith('新分组', '描述')
    expect(listWatchlistGroups).toHaveBeenCalled()
  })

  it('addGroup 失败返回 false', async () => {
    vi.mocked(createWatchlistGroup).mockRejectedValue(new Error('重名'))
    const store = useWatchlistStore()

    const ok = await store.addGroup('重复名')

    expect(ok).toBe(false)
  })
})
